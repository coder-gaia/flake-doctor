"""The tool-using fixer: unlike baselines.single_prompt (B1), this agent
can read the actual production source, look at other test files, and run
the suite itself before deciding it is done.

Phase 4 uses this with zero verification retries -- that is B2, the "same
agent, no verification loop" ablation the plan calls for: same tools,
same model, same prompt as the final agent, so any gap between B2 and the
final agent (Phase 5) isolates exactly what the verification-and-retry
loop is worth. From Phase 5 onward (fix_case_with_verification below),
flakedoctor.verify's feedback gets fed back into the *same*
ClaudeSDKClient session via additional turns, which is why this module is
built around a persistent client instead of one-shot query() calls.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)

from baselines.single_prompt import copy_case_without_answer_key
from flakedoctor.verify import VerificationReport, verify_fix

MODEL = "claude-sonnet-5"

# Enough to read around, run pytest a few times, and edit -- not so much
# that a stuck agent burns an unbounded amount of the shared rate-limit
# window. Revisit with evidence if cases start hitting this ceiling.
DEFAULT_MAX_TURNS = 20

# Narrow on purpose: no Task (no subagents), no WebSearch/WebFetch, no
# CronCreate/RemoteTrigger/etc. Just enough to diagnose and patch a small
# project and check the result. See dev-plan/PLAN.md section 2.
ALLOWED_TOOLS = ["Read", "Grep", "Glob", "Edit", "Write", "Bash"]

SYSTEM_PROMPT = """\
You are a careful software engineer fixing a flaky pytest test. You have \
full read/write access, but only within your working directory (a small, \
self-contained project copy). Do not read, write, or run commands against \
any path outside your working directory, even if it is technically \
reachable -- everything you need to diagnose and fix this is already \
inside it.

Investigate before you change anything:
- Read the failing test and the production code it exercises.
- Look for other test files that might interact with it (shared state, \
execution order, leaked globals, environment variables).
- Run the test suite with Bash (e.g. `python -m pytest tests/ -q`) to \
confirm your understanding of the failure and, once you've made a change, \
to confirm the fix actually works. Rerunning a few times is reasonable \
evidence; a single green run is not proof of anything for a flaky test.

Constraints:
- Keep the target test function's exact name unchanged. You may add new \
test functions if that improves coverage.
- Do not weaken or delete assertions, add sleeps/retries/skip markers, or \
otherwise make the symptom disappear without fixing the underlying cause.
- When you believe the fix is complete and you've verified it by running \
the suite, say so briefly and stop. Don't keep exploring past that point.\
"""

INITIAL_PROMPT_TEMPLATE = """\
The test `{target_test}` in this project is flaky: it sometimes fails when \
rerun, even though nothing about the underlying code changes between runs.

Diagnose the root cause and fix it."""

# Retries beyond the first attempt. 2 extra tries (3 total) was picked as a
# starting budget, not derived from data yet -- Phase 6 measures whether
# retry N+1 earns enough extra Verified Repair Rate to justify its cost
# and revises this with evidence, per dev-plan/PLAN.md section 6.
DEFAULT_MAX_RETRIES = 2

# ClaudeAgentOptions.max_turns caps the whole ClaudeSDKClient session, not
# each individual query() call -- so a client driving up to
# DEFAULT_MAX_RETRIES+1 attempts needs enough budget for all of them
# combined, not just one. The single hard-case smoke test used 14 turns
# for a full diagnose-fix-verify cycle; sized with headroom for three such
# cycles rather than measured precisely yet.
DEFAULT_MAX_TURNS_WITH_RETRY = 45

FEEDBACK_TEMPLATE = """\
Your fix did not pass verification. An automated checker found:

{feedback}

Notes on what each failing gate means:
- "stability" failing: the target test (or the whole suite) is still not \
100% reliable across reruns.
- "sensitivity" failing: a known real bug was injected into the production \
code, and nothing in the suite caught it. This usually means the flake got \
fixed without the underlying behavior actually being tested -- consider \
whether you need to *add* coverage, not just make the existing test pass.
- "anti_cheat" failing: something about your change looks like it masks \
the symptom (sleep/skip/retry markers, or fewer assertions than before) \
rather than fixing the cause.
- "blast_radius" failing: something else in the suite broke.

Revise the fix accordingly, then verify it yourself again before finishing."""


@dataclass
class AgentRun:
    candidate_dir: Path
    messages: list[Any] = field(default_factory=list)
    final_text: str = ""
    num_turns: int = 0
    cost_usd: float = 0.0


@dataclass
class VerifiedFixResult:
    candidate_dir: Path
    verification: VerificationReport
    attempts: int
    runs: list[AgentRun] = field(default_factory=list)

    @property
    def total_cost_usd(self) -> float:
        return sum(r.cost_usd for r in self.runs)


def _record_response(run: AgentRun, message: Any) -> None:
    run.messages.append(message)
    if isinstance(message, AssistantMessage):
        for block in message.content:
            if isinstance(block, TextBlock):
                run.final_text = block.text
    if isinstance(message, ResultMessage):
        run.num_turns = message.num_turns
        run.cost_usd = message.total_cost_usd or 0.0


def _build_options(candidate_dir: Path, max_turns: int) -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        tools=ALLOWED_TOOLS,
        setting_sources=[],
        cwd=str(candidate_dir),
        permission_mode="bypassPermissions",  # sandboxed scratch copy, no answer key -- see copy_case_without_answer_key
        max_turns=max_turns,
        model=MODEL,
        system_prompt=SYSTEM_PROMPT,
    )


async def _run_once(candidate_dir: Path, target_test: str, max_turns: int) -> AgentRun:
    prompt = INITIAL_PROMPT_TEMPLATE.format(target_test=target_test)
    options = _build_options(candidate_dir, max_turns)
    run = AgentRun(candidate_dir=candidate_dir)
    async with ClaudeSDKClient(options=options) as client:
        await client.query(prompt)
        async for message in client.receive_response():
            _record_response(run, message)
    return run


async def _run_with_verification(
    original_case_dir: Path,
    candidate_dir: Path,
    target_test: str,
    max_turns: int,
    max_retries: int,
    verify_reruns: int,
) -> VerifiedFixResult:
    """Same agent, same tools, same prompt as _run_once -- the only
    difference from B2 is this loop: after each attempt, run the real
    four-gate verifier and, on failure, send the structured feedback back
    into the *same conversation* (so the model keeps whatever context it
    already built) for another attempt.
    """
    prompt = INITIAL_PROMPT_TEMPLATE.format(target_test=target_test)
    options = _build_options(candidate_dir, max_turns)
    runs: list[AgentRun] = []

    async with ClaudeSDKClient(options=options) as client:
        await client.query(prompt)
        run = AgentRun(candidate_dir=candidate_dir)
        async for message in client.receive_response():
            _record_response(run, message)
        runs.append(run)

        for attempt in range(max_retries + 1):
            report = verify_fix(original_case_dir, candidate_dir, target_test, reruns=verify_reruns)
            if report.all_passed or attempt == max_retries:
                return VerifiedFixResult(candidate_dir, report, attempts=attempt + 1, runs=runs)

            await client.query(FEEDBACK_TEMPLATE.format(feedback=report.as_feedback()))
            run = AgentRun(candidate_dir=candidate_dir)
            async for message in client.receive_response():
                _record_response(run, message)
            runs.append(run)

    # Unreachable (the loop above always returns), but keeps type checkers happy.
    raise RuntimeError("verification retry loop exited without a result")


def run_agent_on_case(
    original_case_dir: Path, candidate_dir: Path, target_test: str, max_turns: int = DEFAULT_MAX_TURNS,
) -> Path:
    """Fixer-shaped entrypoint matching baselines.single_prompt.run_baseline_on_case,
    so flakedoctor.eval can drive either one uniformly. The trajectory
    (run.messages) is discarded here -- flakedoctor.eval callers that want
    it should call _run_once/fix_case directly. See flakedoctor.trajectory
    (Phase 7) for turning it into a required-deliverable artifact.
    """
    candidate_dir = copy_case_without_answer_key(original_case_dir, candidate_dir)
    asyncio.run(_run_once(candidate_dir, target_test, max_turns))
    return candidate_dir


def fix_case(candidate_dir: Path, target_test: str, max_turns: int = DEFAULT_MAX_TURNS) -> AgentRun:
    """Like run_agent_on_case, but returns the full AgentRun (trajectory,
    cost, turn count) instead of just the path. `candidate_dir` must
    already be an isolated copy without the answer key.
    """
    return asyncio.run(_run_once(candidate_dir, target_test, max_turns))


def run_verified_agent_on_case(
    original_case_dir: Path,
    candidate_dir: Path,
    target_test: str,
    max_turns: int = DEFAULT_MAX_TURNS_WITH_RETRY,
    max_retries: int = DEFAULT_MAX_RETRIES,
    verify_reruns: int = 30,
) -> Path:
    """Fixer-shaped entrypoint (matches run_baseline_on_case /
    run_agent_on_case) for flakedoctor.eval, wired to the verify-and-retry
    loop -- this is the final agent, Phase 5 onward. Verification here is
    only to drive the retry loop; flakedoctor.eval still verifies the
    returned candidate_dir itself afterward the same way it does for B1
    and B2, so the reported result is never "trust me, I already checked."
    """
    candidate_dir = copy_case_without_answer_key(original_case_dir, candidate_dir)
    asyncio.run(_run_with_verification(
        original_case_dir, candidate_dir, target_test, max_turns, max_retries, verify_reruns,
    ))
    return candidate_dir


def fix_case_with_verification(
    original_case_dir: Path,
    candidate_dir: Path,
    target_test: str,
    max_turns: int = DEFAULT_MAX_TURNS_WITH_RETRY,
    max_retries: int = DEFAULT_MAX_RETRIES,
    verify_reruns: int = 30,
) -> VerifiedFixResult:
    """Like run_verified_agent_on_case, but returns the full result
    (verification report, attempt count, every attempt's trajectory)
    instead of just the path. `candidate_dir` must already be an isolated
    copy without the answer key.
    """
    return asyncio.run(_run_with_verification(
        original_case_dir, candidate_dir, target_test, max_turns, max_retries, verify_reruns,
    ))


def _print_trajectory(messages: list[Any]) -> None:
    for message in messages:
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, ToolUseBlock):
                    print(f"TOOL_USE: {block.name} {block.input}")
                elif isinstance(block, TextBlock) and block.text:
                    print(f"TEXT: {block.text}")
        elif isinstance(message, UserMessage):
            for block in message.content:
                if isinstance(block, ToolResultBlock):
                    content = block.content if isinstance(block.content, str) else str(block.content)
                    print(f"TOOL_RESULT: {content[:300]}")


def _main() -> None:
    import argparse
    import tempfile

    parser = argparse.ArgumentParser(description="Run the tool-using agent on one case.")
    parser.add_argument("case_dir", type=Path)
    parser.add_argument("target_test")
    parser.add_argument("--max-turns", type=int, default=None, help=f"default {DEFAULT_MAX_TURNS} (B2) or {DEFAULT_MAX_TURNS_WITH_RETRY} (--verify)")
    parser.add_argument("--verify", action="store_true", help="use the verify-and-retry loop (Phase 5) instead of B2's single shot")
    parser.add_argument("--max-retries", type=int, default=DEFAULT_MAX_RETRIES)
    parser.add_argument("--reruns", type=int, default=30, help="stability reruns per verification pass")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    if args.max_turns is None:
        args.max_turns = DEFAULT_MAX_TURNS_WITH_RETRY if args.verify else DEFAULT_MAX_TURNS

    with tempfile.TemporaryDirectory() as tmp:
        candidate = copy_case_without_answer_key(args.case_dir, Path(tmp) / "candidate")

        if args.verify:
            result = asyncio.run(_run_with_verification(
                args.case_dir, candidate, args.target_test, args.max_turns, args.max_retries, args.reruns,
            ))
            if args.verbose:
                for i, run in enumerate(result.runs):
                    print(f"=== attempt {i + 1} ===")
                    _print_trajectory(run.messages)
            print(f"\n--- verification after {result.attempts} attempt(s) ---")
            print(result.verification.as_feedback())
            print("VERDICT:", "PASS" if result.verification.all_passed else "FAIL")
            print(f"total cost_usd={result.total_cost_usd:.4f}")
        else:
            run = asyncio.run(_run_once(candidate, args.target_test, args.max_turns))
            if args.verbose:
                _print_trajectory(run.messages)
            print(f"\n--- final text ---\n{run.final_text}")
            print(f"\n--- turns={run.num_turns} cost_usd={run.cost_usd:.4f} ---")

        file_part, _ = args.target_test.split("::", 1)
        print(f"\n--- resulting {file_part} ---")
        print((candidate / file_part).read_text(encoding="utf-8"))


if __name__ == "__main__":
    _main()
