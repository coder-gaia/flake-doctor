"""Deterministic flake detection.

Reproduces a test's flakiness by running it as a fresh `python -m pytest`
subprocess N times, not by looping in-process. That distinction is not
cosmetic: benchmark/cases/random_set_iteration_order only flakes across
fresh processes (PYTHONHASHSEED is fixed for the life of one process), so
an in-process rerun loop would silently report it as stable.

Each run's outcome is read from a JUnit XML report rather than parsed out
of stdout text, because a target test's own per-node result (not the
process exit code) is what actually distinguishes "flaky" from "reliably
broken" for benchmark/cases/order_dependence_singleton_reset and
benchmark/cases/shared_state_mutable_default_arg: both have two tests that
fail symmetrically (exactly one always fails, whichever ran second), so
the whole-run exit code is nonzero on every single run regardless of
which order occurred.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RunResult:
    """The outcome of one fresh-process pytest invocation."""

    passed: bool
    found: bool  # False means the target test node wasn't in the report at all
    message: str  # failure/error text when not passed, else ""
    returncode: int
    stdout: str
    stderr: str


@dataclass
class DetectionReport:
    case_dir: Path
    target_test: str
    runs: list[RunResult] = field(default_factory=list)

    @property
    def reruns(self) -> int:
        return len(self.runs)

    @property
    def fail_count(self) -> int:
        return sum(1 for r in self.runs if not r.passed)

    @property
    def flake_rate(self) -> float:
        if not self.runs:
            return 0.0
        return self.fail_count / len(self.runs)

    def sample_failure(self) -> RunResult | None:
        """One failing run, to show as evidence -- e.g. in a trajectory or
        the improvement changelog."""
        for r in self.runs:
            if not r.passed:
                return r
        return None


def _split_target(target_test: str) -> tuple[str, str]:
    """"tests/test_x.py::test_y" -> ("tests/test_x.py", "test_y")."""
    file_part, _, func_part = target_test.partition("::")
    if not func_part:
        raise ValueError(f"target_test must be '<file>::<function>', got {target_test!r}")
    return file_part, func_part


def _expected_classname(file_part: str) -> str:
    """"tests/test_x.py" -> "tests.test_x", matching pytest's junit classname."""
    return file_part[:-3].replace("/", ".").replace("\\", ".") if file_part.endswith(".py") else file_part


def _parse_junit(report_path: Path, target_test: str) -> tuple[bool, bool, str]:
    """Returns (passed, found, message) for the named test node."""
    file_part, func_name = _split_target(target_test)
    expected_classname = _expected_classname(file_part)

    if not report_path.exists():
        return False, False, "no junit report produced (collection error?)"

    tree = ET.parse(report_path)
    root = tree.getroot()
    # pytest emits either <testsuites><testsuite>...</testsuite></testsuites>
    # or a bare <testsuite> depending on version -- handle both.
    testcases = root.findall(".//testcase")

    candidates = [tc for tc in testcases if tc.get("name") == func_name]
    # Prefer an exact classname match when more than one test shares a name.
    exact = [tc for tc in candidates if (tc.get("classname") or "").endswith(expected_classname)]
    match = exact[0] if exact else (candidates[0] if candidates else None)

    if match is None:
        return False, False, f"test node {target_test!r} not found in junit report"

    failure = match.find("failure")
    error = match.find("error")
    skipped = match.find("skipped")
    if failure is not None:
        return False, True, failure.get("message", "") or (failure.text or "")
    if error is not None:
        return False, True, error.get("message", "") or (error.text or "")
    if skipped is not None:
        # A skipped test is not a verified pass: @pytest.mark.skip is
        # exactly the kind of "fix" this harness exists to reject, so a
        # skipped target test counts as a failed run, not a stable one.
        msg = skipped.get("message", "") or (skipped.text or "") or "test was skipped"
        return False, True, f"skipped (treated as failure): {msg}"
    return True, True, ""


def run_once(case_dir: Path, target_test: str, extra_args: list[str] | None = None) -> RunResult:
    """Run the case's whole tests/ directory once, as a fresh subprocess.

    Collecting the whole tests/ directory (not just the target test's own
    file) matters for order-dependence cases: pytest-randomly can only
    shuffle relative order across files it actually collected.
    """
    case_dir = Path(case_dir)
    with tempfile.TemporaryDirectory() as tmp:
        report_path = Path(tmp) / "report.xml"
        cmd = [
            sys.executable, "-m", "pytest", "tests",
            f"--junitxml={report_path}", "-q", "--no-header",
        ]
        if extra_args:
            cmd.extend(extra_args)
        proc = subprocess.run(
            cmd, cwd=case_dir, capture_output=True, text=True, timeout=120,
        )
        passed, found, message = _parse_junit(report_path, target_test)
        return RunResult(
            passed=passed, found=found, message=message,
            returncode=proc.returncode, stdout=proc.stdout, stderr=proc.stderr,
        )


def detect(case_dir: Path, target_test: str, reruns: int = 50) -> DetectionReport:
    """Run the target test `reruns` times, each a fresh subprocess."""
    report = DetectionReport(case_dir=Path(case_dir), target_test=target_test)
    for _ in range(reruns):
        report.runs.append(run_once(case_dir, target_test))
    return report


def _main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Measure a case's empirical flake rate.")
    parser.add_argument("case_dir", type=Path, help="e.g. benchmark/cases/timing_ttl_second_boundary")
    parser.add_argument("target_test", help="e.g. tests/test_ttl_cache.py::test_set_then_get_within_ttl")
    parser.add_argument("--reruns", type=int, default=50)
    args = parser.parse_args()

    report = detect(args.case_dir, args.target_test, reruns=args.reruns)
    print(f"{args.target_test}: {report.fail_count}/{report.reruns} failed ({report.flake_rate:.1%})")
    failure = report.sample_failure()
    if failure is not None:
        print("\nSample failure:")
        print(failure.message.strip() or failure.stdout[-2000:])


if __name__ == "__main__":
    _main()
