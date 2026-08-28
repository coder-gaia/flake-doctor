"""Run a fixer (B1, B2, or the final agent) across every benchmark case
and verify each result, producing the primary comparison the challenge
brief asks for: the same cases, the same verifier, applied after the
fact so no fixer sees it during its own run.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

import yaml

from flakedoctor.verify import GateResult, verify_fix

REPO_ROOT = Path(__file__).resolve().parents[1]
CASES_DIR = REPO_ROOT / "benchmark" / "cases"
RESULTS_DIR = REPO_ROOT / "results"

FixerFn = Callable[[Path, Path, str], Path]


@dataclass
class CaseResult:
    case: str
    verdict: str  # PASS, FAIL, ERROR, or SANDBOX_VIOLATION
    gates: dict[str, bool] = field(default_factory=dict)
    detail: dict[str, str] = field(default_factory=dict)
    error: str | None = None
    seconds: float = 0.0
    sandbox_violations: list[str] = field(default_factory=list)


def _git_modified_tracked_files() -> set[str]:
    """Repo-root-relative paths of tracked files with uncommitted
    modifications, excluding results/ (the one place this module is
    *supposed* to write). A tool-using fixer has Bash/Read/Edit/Write with
    no path restriction beyond its cwd (see agent.py's docstring on why:
    Windows doesn't support the SDK's Bash sandbox, and the documented
    alternative -- Read/Edit permission deny-rules -- wasn't worth
    building out under the hackathon clock). This is the automated,
    unattended equivalent of ground rule 04's "human approval before a
    consequential action": every case's tracked-file footprint is
    diffed and any change outside results/ is reverted immediately.
    """
    proc = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    modified = set()
    for line in proc.stdout.splitlines():
        path = line[3:].strip().strip('"')
        if path and not path.startswith("results/") and not path.startswith("results\\"):
            modified.add(path)
    return modified


def _revert_paths(paths: set[str]) -> None:
    if paths:
        subprocess.run(["git", "checkout", "--"] + sorted(paths), cwd=REPO_ROOT, capture_output=True, text=True)


def load_cases() -> list[tuple[Path, str]]:
    cases = []
    for case_dir in sorted(CASES_DIR.iterdir()):
        case_yaml = case_dir / "case.yaml"
        if not case_dir.is_dir() or not case_yaml.exists():
            continue
        with open(case_yaml, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        cases.append((case_dir, data["target_test"]))
    return cases


def run_fixer_eval(
    fixer_fn: FixerFn, reruns: int = 30, verbose: bool = True, persist_label: str | None = None,
) -> list[CaseResult]:
    """The fixer always does its live work in a real OS temp directory
    (never under the repo, and never at a path that echoes
    benchmark/cases/<case>/ back at it -- see CHANGELOG.md for the
    environment_decimal_context_leak incident this fixes). If
    persist_label is given, the *final* state is copied into
    results/candidates/<persist_label>/<case>/ afterward, as a snapshot
    for evidence, not as the live workspace.

    Every case's tracked-file footprint outside results/ is diffed
    before and after; any change is reverted immediately and recorded as
    a SANDBOX_VIOLATION rather than silently trusted.
    """
    results: list[CaseResult] = []
    for case_dir, target_test in load_cases():
        start = time.monotonic()
        before = _git_modified_tracked_files()
        with tempfile.TemporaryDirectory() as tmp:
            candidate = Path(tmp) / "candidate"
            try:
                candidate = fixer_fn(case_dir, candidate, target_test)
                report = verify_fix(case_dir, candidate, target_test, reruns=reruns)
                gates: dict[str, bool] = {g.name: g.passed for g in report.gates}
                detail: dict[str, str] = {g.name: g.detail for g in report.gates}
                verdict = "PASS" if report.all_passed else "FAIL"
                result = CaseResult(case=case_dir.name, verdict=verdict, gates=gates, detail=detail)
            except Exception as e:  # a fixer crashing on one case must not kill the whole eval
                result = CaseResult(case=case_dir.name, verdict="ERROR", error=str(e))
            finally:
                # Persist whatever exists even on error/timeout -- an ERROR
                # with no artifact to inspect afterward is a dead end. See
                # CHANGELOG.md, shared_state_class_level_attribute's
                # unreproduced subprocess timeout: the first time this
                # happened, the candidate had already been cleaned up by
                # the time anyone could look at what the agent had written.
                if persist_label and candidate.exists():
                    snapshot_dir = RESULTS_DIR / "candidates" / persist_label / case_dir.name
                    if snapshot_dir.exists():
                        shutil.rmtree(snapshot_dir)
                    shutil.copytree(candidate, snapshot_dir)

        violations = _git_modified_tracked_files() - before
        if violations:
            _revert_paths(violations)
            result.sandbox_violations = sorted(violations)
            result.verdict = "SANDBOX_VIOLATION"
            if verbose:
                print(f"WARNING: {result.case} wrote outside its sandbox: {violations} -- reverted.")

        result.seconds = time.monotonic() - start
        results.append(result)
        if verbose:
            print(f"{result.case}: {result.verdict} ({result.seconds:.1f}s) {result.gates}")
    return results


def summarize(results: list[CaseResult]) -> dict:
    total = len(results)
    passed = sum(1 for r in results if r.verdict == "PASS")
    sandbox_violations = sum(1 for r in results if r.verdict == "SANDBOX_VIOLATION")
    gate_fail_counts: dict[str, int] = {}
    for r in results:
        for gate, ok in r.gates.items():
            if not ok:
                gate_fail_counts[gate] = gate_fail_counts.get(gate, 0) + 1
    return {
        "total_cases": total,
        "verified_repair_rate": passed / total if total else 0.0,
        "passed": passed,
        "failed_or_errored": total - passed,
        "sandbox_violations": sandbox_violations,
        "gate_failure_counts": gate_fail_counts,
    }


def save_results(label: str, results: list[CaseResult]) -> Path:
    RESULTS_DIR.mkdir(exist_ok=True)
    out_path = RESULTS_DIR / f"{label}.json"
    payload = {"summary": summarize(results), "cases": [asdict(r) for r in results]}
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out_path


def _main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run a fixer across all benchmark cases.")
    parser.add_argument("fixer", choices=["b1", "b2", "final"], help="which fixer to evaluate")
    parser.add_argument("--reruns", type=int, default=30)
    parser.add_argument("--no-persist", action="store_true", help="don't keep candidate artifacts")
    args = parser.parse_args()

    if args.fixer == "b1":
        from baselines.single_prompt import run_baseline_on_case as fixer_fn
        label = "b1_baseline"
    elif args.fixer == "b2":
        from flakedoctor.agent import run_agent_on_case as fixer_fn
        label = "b2_agent_no_verification"
    elif args.fixer == "final":
        from flakedoctor.agent import run_verified_agent_on_case as fixer_fn
        label = "final_verified_agent"

    results = run_fixer_eval(fixer_fn, reruns=args.reruns, persist_label=None if args.no_persist else label)
    summary = summarize(results)
    print("\n--- Summary ---")
    print(json.dumps(summary, indent=2))
    out_path = save_results(label, results)
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    _main()
