"""B1: the baseline the challenge brief itself suggests, "one direct
prompt with basic instructions." No tools, no test execution, no
iteration -- the model sees the flaky test file once and returns a fix.

This is deliberately the least capable thing that could plausibly work:
whatever the final agent does better than this has to be explained by a
specific design choice (context, tools, verification, retries), not by
"we used a bigger model" -- B1 and the final agent use the same model.
"""
from __future__ import annotations

import asyncio
import re
import shutil
from pathlib import Path

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock, query

MODEL = "claude-sonnet-5"

PROMPT_TEMPLATE = """\
The following pytest test is flaky: it sometimes fails when rerun, even though nothing about the code under test changed between runs.

File: {file_path}

```python
{file_content}
```

Fix the test so it passes reliably every time it runs. You may add new test functions if that helps cover the behavior properly, but the function shown above must keep its exact name -- do not rename it, even if a different name would read better. Return ONLY the complete, corrected content of the file -- the whole file, not a diff or an excerpt -- inside a single Python code block. Do not include any explanation before or after the code block.
"""


def _extract_code_block(text: str) -> str:
    match = re.search(r"```(?:python)?\s*\n(.*?)```", text, flags=re.DOTALL)
    if match:
        return match.group(1).rstrip() + "\n"
    # Defensive fallback: no fence found, use the raw response as-is.
    return text.strip() + "\n"


async def _ask_for_fix(file_path: str, file_content: str) -> str:
    prompt = PROMPT_TEMPLATE.format(file_path=file_path, file_content=file_content)
    stderr_lines: list[str] = []
    options = ClaudeAgentOptions(
        tools=[],  # the tool universe itself is empty -- allowed_tools=[] alone
                   # does NOT do this; it only filters a default toolset that
                   # is otherwise the full Claude Code preset (confirmed live:
                   # allowed_tools=[] still let the model call Bash/Glob/Read).
        setting_sources=[],  # don't inherit this dev session's project/user settings
        max_turns=1,
        model=MODEL,
        system_prompt="You are a careful software engineer. Follow the user's output format exactly.",
        stderr=stderr_lines.append,
    )
    response_text = ""
    try:
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        response_text += block.text
    except Exception:
        if stderr_lines:
            print("stderr from claude CLI subprocess:", "".join(stderr_lines)[-3000:])
        raise
    return response_text


def propose_fix(file_path: str, file_content: str) -> str:
    """Synchronous wrapper: one direct prompt in, one fixed file out."""
    response_text = asyncio.run(_ask_for_fix(file_path, file_content))
    return _extract_code_block(response_text)


def copy_case_without_answer_key(original_case_dir: Path, candidate_dir: Path) -> Path:
    """Copy only what a fixer is allowed to see: conftest.py, src/, tests/.

    Never copy mutant/ or case.yaml. mutant/ contains the exact bug V2's
    sensitivity gate checks for, and case.yaml's `notes` / `what_it_breaks`
    fields describe that same bug in prose, and for order_dependence_cross_file
    even name the culprit test outright -- either one, visible to a fixer,
    would make the fix trivial instead of diagnosed. This isolation applies
    to every fixer (B1, B2, and the final agent) equally, so the comparison
    stays fair.
    """
    original_case_dir = Path(original_case_dir)
    candidate_dir = Path(candidate_dir)
    if candidate_dir.exists():
        shutil.rmtree(candidate_dir)
    candidate_dir.mkdir(parents=True)

    shutil.copy2(original_case_dir / "conftest.py", candidate_dir / "conftest.py")
    shutil.copytree(original_case_dir / "src", candidate_dir / "src")
    shutil.copytree(original_case_dir / "tests", candidate_dir / "tests")
    return candidate_dir


def run_baseline_on_case(original_case_dir: Path, candidate_dir: Path, target_test: str) -> Path:
    """Copy the case (minus the answer key) to `candidate_dir`, overwrite
    the target test file with B1's proposed fix, and return `candidate_dir`
    (ready for verify_fix, which reads the mutant from `original_case_dir`
    separately -- the fixer never touches it).
    """
    file_part, _ = target_test.split("::", 1)
    original_case_dir = Path(original_case_dir)
    candidate_dir = copy_case_without_answer_key(original_case_dir, candidate_dir)

    original_content = (original_case_dir / file_part).read_text(encoding="utf-8")
    fixed_content = propose_fix(file_part, original_content)
    (candidate_dir / file_part).write_text(fixed_content, encoding="utf-8")

    return candidate_dir


def _main() -> None:
    import argparse
    import tempfile

    parser = argparse.ArgumentParser(description="Run the B1 single-prompt baseline on one case.")
    parser.add_argument("case_dir", type=Path)
    parser.add_argument("target_test")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        candidate = run_baseline_on_case(args.case_dir, Path(tmp) / "candidate", args.target_test)
        file_part, _ = args.target_test.split("::", 1)
        print(f"--- B1 proposed fix for {file_part} ---")
        print((candidate / file_part).read_text(encoding="utf-8"))


if __name__ == "__main__":
    _main()
