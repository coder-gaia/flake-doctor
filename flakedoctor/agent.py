"""The tool-using fixer: unlike baselines.single_prompt (B1), this agent
can read the actual production source, look at other test files, and run
the suite itself before deciding it is done.

Phase 4 uses this with zero verification retries -- that is B2, the "same
agent, no verification loop" ablation the plan calls for: same tools,
same model, same prompt as the final agent, so any gap between B2 and the
final agent (Phase 5) isolates exactly what the verification-and-retry
loop is worth. From Phase 5 onward, flakedoctor.verify's feedback gets
fed back into the *same* ClaudeSDKClient session via additional turns,
which is why this module is built around a persistent client instead of
one-shot query() calls.
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


@dataclass
class AgentRun:
    candidate_dir: Path
    messages: list[Any] = field(default_factory=list)
    final_text: str = ""
    num_turns: int = 0
    cost_usd: float = 0.0


async def _run_once(candidate_dir: Path, target_test: str, max_turns: int) -> AgentRun:
    prompt = INITIAL_PROMPT_TEMPLATE.format(target_test=target_test)
    options = ClaudeAgentOptions(
        tools=ALLOWED_TOOLS,
        setting_sources=[],
        cwd=str(candidate_dir),
        permission_mode="bypassPermissions",  # sandboxed scratch copy, no answer key -- see copy_case_without_answer_key
        max_turns=max_turns,
        model=MODEL,
        system_prompt=SYSTEM_PROMPT,
    )
    run = AgentRun(candidate_dir=candidate_dir)
    async with ClaudeSDKClient(options=options) as client:
        await client.query(prompt)
        async for message in client.receive_response():
            run.messages.append(message)
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        run.final_text = block.text
            if isinstance(message, ResultMessage):
                run.num_turns = message.num_turns
                run.cost_usd = message.total_cost_usd or 0.0
    return run


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


def _main() -> None:
    import argparse
    import tempfile

    parser = argparse.ArgumentParser(description="Run the tool-using agent (B2, no verification) on one case.")
    parser.add_argument("case_dir", type=Path)
    parser.add_argument("target_test")
    parser.add_argument("--max-turns", type=int, default=DEFAULT_MAX_TURNS)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        candidate = copy_case_without_answer_key(args.case_dir, Path(tmp) / "candidate")
        run = asyncio.run(_run_once(candidate, args.target_test, args.max_turns))

        if args.verbose:
            for message in run.messages:
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

        print(f"\n--- final text ---\n{run.final_text}")
        print(f"\n--- turns={run.num_turns} cost_usd={run.cost_usd:.4f} ---")
        file_part, _ = args.target_test.split("::", 1)
        print(f"\n--- resulting {file_part} ---")
        print((candidate / file_part).read_text(encoding="utf-8"))


if __name__ == "__main__":
    _main()
