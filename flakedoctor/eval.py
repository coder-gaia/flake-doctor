"""Run a fixer (B1, B2, or the final agent) across every benchmark case
and verify each result, producing the primary comparison the challenge
brief asks for: the same cases, the same verifier, applied after the
fact so no fixer sees it during its own run.
"""
from __future__ import annotations

import json
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

import yaml

from flakedoctor.verify import GateResult, verify_fix

CASES_DIR = Path(__file__).resolve().parents[1] / "benchmark" / "cases"
RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"

FixerFn = Callable[[Path, Path, str], Path]


@dataclass
class CaseResult:
    case: str
    verdict: str  # PASS, FAIL, or ERROR
    gates: dict[str, bool] = field(default_factory=dict)
    detail: dict[str, str] = field(default_factory=dict)
    error: str | None = None
    seconds: float = 0.0


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
    """persist_label, if given, keeps each case's candidate fix under
    results/candidates/<persist_label>/<case>/ instead of a throwaway temp
    dir -- real artifacts for the changelog and the video, not just a
    pass/fail verdict.
    """
    results: list[CaseResult] = []
    for case_dir, target_test in load_cases():
        start = time.monotonic()
        try:
            if persist_label:
                candidate_dir = RESULTS_DIR / "candidates" / persist_label / case_dir.name
                candidate = fixer_fn(case_dir, candidate_dir, target_test)
                report = verify_fix(case_dir, candidate, target_test, reruns=reruns)
            else:
                with tempfile.TemporaryDirectory() as tmp:
                    candidate = fixer_fn(case_dir, Path(tmp) / "candidate", target_test)
                    report = verify_fix(case_dir, candidate, target_test, reruns=reruns)
            gates: dict[str, bool] = {g.name: g.passed for g in report.gates}
            detail: dict[str, str] = {g.name: g.detail for g in report.gates}
            verdict = "PASS" if report.all_passed else "FAIL"
            result = CaseResult(case=case_dir.name, verdict=verdict, gates=gates, detail=detail)
        except Exception as e:  # a fixer crashing on one case must not kill the whole eval
            result = CaseResult(case=case_dir.name, verdict="ERROR", error=str(e))
        result.seconds = time.monotonic() - start
        results.append(result)
        if verbose:
            print(f"{result.case}: {result.verdict} ({result.seconds:.1f}s) {result.gates}")
    return results


def summarize(results: list[CaseResult]) -> dict:
    total = len(results)
    passed = sum(1 for r in results if r.verdict == "PASS")
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
    parser.add_argument("fixer", choices=["b1"], help="which fixer to evaluate")
    parser.add_argument("--reruns", type=int, default=30)
    parser.add_argument("--no-persist", action="store_true", help="don't keep candidate artifacts")
    args = parser.parse_args()

    if args.fixer == "b1":
        from baselines.single_prompt import run_baseline_on_case as fixer_fn
        label = "b1_baseline"

    results = run_fixer_eval(fixer_fn, reruns=args.reruns, persist_label=None if args.no_persist else label)
    summary = summarize(results)
    print("\n--- Summary ---")
    print(json.dumps(summary, indent=2))
    out_path = save_results(label, results)
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    _main()
