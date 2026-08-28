"""One-off script: captures real trajectories for deliverable 4 by
actually running the agents (costs real, if small, notional API usage)
and rendering the result via flakedoctor.trajectory.

Not part of the library -- flakedoctor/eval.py doesn't call this
automatically, so a 14-case evaluation run never pays for trajectory
capture it doesn't need. Representative trajectories only, per the
challenge brief, not one per case.
"""
import shutil
import tempfile
from pathlib import Path

from baselines.single_prompt import copy_case_without_answer_key
from flakedoctor.agent import (
    ALLOWED_TOOLS,
    INITIAL_PROMPT_TEMPLATE,
    SYSTEM_PROMPT,
    fix_case,
    fix_case_with_verification,
)
from flakedoctor.trajectory import save
from flakedoctor.verify import verify_fix

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "trajectories"


def capture_b2(case_id: str, target_test: str) -> None:
    """B2: single shot, no internal verification loop -- verify separately
    afterward so the trajectory can still show the real verdict.
    """
    case_dir = REPO_ROOT / "benchmark" / "cases" / case_id
    with tempfile.TemporaryDirectory() as tmp:
        candidate = copy_case_without_answer_key(case_dir, Path(tmp) / "candidate")
        run = fix_case(candidate, target_test)
        report = verify_fix(case_dir, candidate, target_test, reruns=30)
        save(
            case_id=f"b2_{case_id}",
            instructions=SYSTEM_PROMPT,
            initial_prompt=INITIAL_PROMPT_TEMPLATE.format(target_test=target_test),
            attempts=[run.messages],
            out_dir=OUT_DIR,
            final_verdict=report.as_feedback() + f"\nVERDICT: {'PASS' if report.all_passed else 'FAIL'}",
        )
    print(f"b2_{case_id}: saved, cost=${run.cost_usd:.4f}, verdict={'PASS' if report.all_passed else 'FAIL'}")


def capture_final(case_id: str, target_test: str, verify_reruns: int = 30) -> None:
    """The verified agent: real verify-and-retry loop."""
    case_dir = REPO_ROOT / "benchmark" / "cases" / case_id
    with tempfile.TemporaryDirectory() as tmp:
        candidate = copy_case_without_answer_key(case_dir, Path(tmp) / "candidate")
        result = fix_case_with_verification(case_dir, candidate, target_test, verify_reruns=verify_reruns)
        save(
            case_id=f"final_{case_id}",
            instructions=SYSTEM_PROMPT,
            initial_prompt=INITIAL_PROMPT_TEMPLATE.format(target_test=target_test),
            attempts=[r.messages for r in result.runs],
            out_dir=OUT_DIR,
            feedback_between_attempts=result.feedback_history,
            final_verdict=result.verification.as_feedback()
            + f"\nVERDICT: {'PASS' if result.verification.all_passed else 'FAIL'}",
        )
    verdict = "PASS" if result.verification.all_passed else "FAIL"
    print(f"final_{case_id}: saved, attempts={result.attempts}, cost=${result.total_cost_usd:.4f}, verdict={verdict}")


if __name__ == "__main__":
    import sys

    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("b2", "all"):
        capture_b2("order_dependence_cross_file", "tests/test_billing.py::test_new_user_pays_full_price")
    if which in ("final", "all"):
        capture_final("order_dependence_fixture_leak", "tests/test_inventory.py::test_catalog_starts_empty_for_a_fresh_scenario")
