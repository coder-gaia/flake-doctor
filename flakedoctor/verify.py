"""Four deterministic gates a candidate fix must pass before it is trusted.

A candidate fix is a directory shaped like a benchmark case (conftest.py,
src/, tests/) with the agent's changes applied -- always a scratch copy,
never the checked-in original (see docs on the checkpoint-before-action
ground rule: patching a real tree is a consequential action).

    V1 stability     0/N reruns fail, across fresh subprocesses.
    V2 sensitivity   the case's known mutant, overlaid onto the candidate's
                      src/, must still make the (now-fixed) test fail. This
                      is the gate that catches a "fix" that made the flake
                      go away by defeating the test's ability to catch a
                      real regression, rather than by fixing the actual
                      race/leak/order bug.
    V3 anti-cheat    an AST scan of the candidate test file rejects
                      sleep-based masking, skip/xfail/flaky markers, and
                      any drop in assertion count versus the original.
    V4 blast radius  the rest of the case's test suite still passes.

V2 and V3 both exist because neither alone is sufficient: a test gutted
down to `assert True` passes V1 (trivially stable) and could pass V2 too
if the mutant's effect isn't otherwise observed, but V3's assertion-count
check catches it. A sleep-based fix might keep every assertion intact and
still pass V3's marker scan while V1 (or a slow V4) exposes it as still
unstable, or V3's sleep-call scan flags it directly.
"""
from __future__ import annotations

import ast
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from flakedoctor.detect import detect, _split_target

FORBIDDEN_CALL_NAMES = {"sleep"}
FORBIDDEN_MARK_NAMES = {"skip", "skipif", "xfail", "flaky"}


@dataclass
class GateResult:
    name: str
    passed: bool
    detail: str


@dataclass
class VerificationReport:
    gates: list[GateResult] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return all(g.passed for g in self.gates)

    def failing(self) -> list[GateResult]:
        return [g for g in self.gates if not g.passed]

    def as_feedback(self) -> str:
        """Structured text handed back to the agent for its next retry."""
        lines = []
        for g in self.gates:
            status = "PASS" if g.passed else "FAIL"
            lines.append(f"[{status}] {g.name}: {g.detail}")
        return "\n".join(lines)


def _load_case_yaml(case_dir: Path) -> dict:
    with open(Path(case_dir) / "case.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def verify_stability(candidate_dir: Path, target_test: str, reruns: int = 50) -> GateResult:
    report = detect(candidate_dir, target_test, reruns=reruns)
    passed = report.flake_rate == 0.0
    detail = f"{report.fail_count}/{report.reruns} fresh-process runs failed"
    if not passed:
        failure = report.sample_failure()
        if failure is not None:
            detail += f"; sample: {failure.message.strip()[:200]}"
    return GateResult("stability", passed, detail)


def verify_sensitivity(original_case_dir: Path, candidate_dir: Path, target_test: str) -> GateResult:
    """The mutant must be caught by *some* test in the suite, not
    necessarily the one originally named as flaky. A legitimate fix may
    split one flaky assertion into two deterministic tests (e.g. a
    same-bucket-hit case and a separate cross-bucket-expiry case); it
    would be wrong to fail a good fix just because the specific behavior
    that catches the mutant moved to a new test function. What's fixed
    (target_test must still exist and be stable) is checked by
    verify_stability; what's checked here is whether the suite as a whole
    still guards against this regression.
    """
    case_yaml = _load_case_yaml(original_case_dir)
    mutant_files = case_yaml["mutant"]["files"]

    with tempfile.TemporaryDirectory() as tmp:
        scratch = Path(tmp) / "mutated"
        shutil.copytree(candidate_dir, scratch)
        for rel_path in mutant_files:
            src_file = Path(original_case_dir) / "mutant" / rel_path
            dst_file = scratch / rel_path
            if not src_file.exists():
                return GateResult(
                    "sensitivity", False,
                    f"mutant file {rel_path} missing from case fixture",
                )
            shutil.copy2(src_file, dst_file)

        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "tests", "-q", "--no-header"],
            cwd=scratch, capture_output=True, text=True, timeout=120,
        )

    if proc.returncode == 0:
        detail = "mutant NOT caught: the whole suite still passes with a known bug injected into production code"
        return GateResult("sensitivity", False, detail)
    tail = "\n".join(proc.stdout.strip().splitlines()[-6:])
    detail = f"mutant correctly caught by the suite: {tail}"
    return GateResult("sensitivity", True, detail)


def _count_asserts(tree: ast.AST) -> int:
    return sum(1 for node in ast.walk(tree) if isinstance(node, ast.Assert))


def _decorator_mark_name(dec: ast.expr) -> str | None:
    target = dec.func if isinstance(dec, ast.Call) else dec
    if isinstance(target, ast.Attribute):
        return target.attr
    return None


def _find_forbidden_patterns(tree: ast.AST) -> list[str]:
    issues = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else (
                func.id if isinstance(func, ast.Name) else None
            )
            if name in FORBIDDEN_CALL_NAMES:
                issues.append(f"call to `{name}(...)` (possible timing-based masking)")
        if isinstance(node, ast.FunctionDef):
            for dec in node.decorator_list:
                mark = _decorator_mark_name(dec)
                if mark in FORBIDDEN_MARK_NAMES:
                    issues.append(f"@pytest.mark.{mark} on {node.name}")
    return issues


def verify_anti_cheat(original_case_dir: Path, candidate_dir: Path, target_test: str) -> GateResult:
    file_part, _ = _split_target(target_test)
    original_file = Path(original_case_dir) / file_part
    candidate_file = Path(candidate_dir) / file_part

    original_tree = ast.parse(original_file.read_text(encoding="utf-8"))
    candidate_tree = ast.parse(candidate_file.read_text(encoding="utf-8"))

    issues = _find_forbidden_patterns(candidate_tree)

    original_asserts = _count_asserts(original_tree)
    candidate_asserts = _count_asserts(candidate_tree)
    if candidate_asserts < original_asserts:
        issues.append(
            f"assert count dropped from {original_asserts} to {candidate_asserts} "
            "(a weakened test can look fixed without actually testing anything)"
        )

    passed = not issues
    detail = "; ".join(issues) if issues else "no forbidden patterns; assert count held or increased"
    return GateResult("anti_cheat", passed, detail)


def verify_blast_radius(candidate_dir: Path) -> GateResult:
    with tempfile.TemporaryDirectory() as tmp:
        report_path = Path(tmp) / "report.xml"
        cmd = [
            sys.executable, "-m", "pytest", "tests",
            f"--junitxml={report_path}", "-q", "--no-header",
        ]
        subprocess.run(cmd, cwd=candidate_dir, capture_output=True, text=True, timeout=120)

        if not report_path.exists():
            return GateResult("blast_radius", False, "no junit report produced (collection error?)")

        root = ET.parse(report_path).getroot()
        suite = root if root.tag == "testsuite" else root.find("testsuite")
        failures = int(suite.get("failures", 0))
        errors = int(suite.get("errors", 0))
        total = int(suite.get("tests", 0))

    passed = failures == 0 and errors == 0
    detail = f"{total - failures - errors}/{total} tests in the case passed"
    return GateResult("blast_radius", passed, detail)


def verify_fix(
    original_case_dir: Path,
    candidate_dir: Path,
    target_test: str,
    reruns: int = 50,
) -> VerificationReport:
    """Run all four gates. Runs every gate even after an early failure --
    the agent's retry does better with a complete list of what's wrong
    than with just the first problem found.
    """
    gates = [
        verify_stability(candidate_dir, target_test, reruns=reruns),
        verify_sensitivity(original_case_dir, candidate_dir, target_test),
        verify_anti_cheat(original_case_dir, candidate_dir, target_test),
        verify_blast_radius(candidate_dir),
    ]
    return VerificationReport(gates=gates)


def _main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run the four verification gates against a candidate fix.")
    parser.add_argument("original_case_dir", type=Path)
    parser.add_argument("candidate_dir", type=Path)
    parser.add_argument("target_test")
    parser.add_argument("--reruns", type=int, default=50)
    args = parser.parse_args()

    report = verify_fix(args.original_case_dir, args.candidate_dir, args.target_test, reruns=args.reruns)
    print(report.as_feedback())
    print()
    print("VERDICT:", "PASS" if report.all_passed else "FAIL")


if __name__ == "__main__":
    _main()
