"""Turns a fixer's raw SDK messages into the two things deliverable 4
("Agent trajectories") asks for: a JSONL trace anyone can parse
mechanically, and a Markdown walkthrough a human can just read start to
finish, including any verification feedback that shaped a retry.

Deliberately built as a standalone step over already-captured messages
(flakedoctor.agent.AgentRun.messages), not baked into the agent loop
itself -- capturing is agent.py's job, rendering is this module's job,
and keeping them separate means either can be tested without the other.
"""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)

MAX_TOOL_RESULT_CHARS = 800


def _to_jsonable(message: Any) -> dict:
    """Best-effort conversion of one SDK message to a plain dict. All the
    message/block types this module has seen (AssistantMessage,
    UserMessage, SystemMessage, ResultMessage, RateLimitEvent, and their
    content blocks) are real dataclasses, so dataclasses.asdict() covers
    the normal case; the repr() fallback exists only for a message shape
    this hasn't encountered yet, so trajectory saving never crashes a run.
    """
    if dataclasses.is_dataclass(message) and not isinstance(message, type):
        return {"type": type(message).__name__, **dataclasses.asdict(message)}
    return {"type": type(message).__name__, "repr": repr(message)}


def _render_message(message: Any) -> list[str]:
    lines: list[str] = []
    if isinstance(message, AssistantMessage):
        for block in message.content:
            if isinstance(block, TextBlock) and block.text.strip():
                lines.append(f"**Agent:** {block.text.strip()}")
            elif isinstance(block, ToolUseBlock):
                lines.append(f"**Tool call** `{block.name}`: `{json.dumps(block.input, default=str)}`")
            # ThinkingBlock is intentionally omitted here: it's internal
            # reasoning, not "what the agent did and how tools responded."
    elif isinstance(message, UserMessage):
        for block in message.content:
            if isinstance(block, ToolResultBlock):
                content = block.content if isinstance(block.content, str) else json.dumps(block.content, default=str)
                content = content.strip()
                if len(content) > MAX_TOOL_RESULT_CHARS:
                    content = content[:MAX_TOOL_RESULT_CHARS] + f"\n... (truncated, {len(content)} chars total)"
                lines.append(f"**Tool result:**\n```\n{content}\n```")
    elif isinstance(message, ResultMessage):
        lines.append(
            f"*(turn {message.num_turns}, cost ${message.total_cost_usd or 0:.4f} notional, "
            f"stop_reason={message.stop_reason})*"
        )
    return lines


def render_markdown(
    case_id: str,
    instructions: str,
    initial_prompt: str,
    attempts: list[list[Any]],
    feedback_between_attempts: list[str] | None = None,
    final_verdict: str | None = None,
) -> str:
    """attempts: one list of raw SDK messages per attempt (len 1 for B2,
    1 + retries for the verified agent). feedback_between_attempts, if
    given, has len(attempts) - 1 entries: the verification feedback sent
    before each retry, i.e. "the feedback that shaped its next step."
    final_verdict, if given, is the four-gate report's own text (e.g.
    VerificationReport.as_feedback()) for whichever attempt closed the
    loop -- shown even when nothing needed a retry, since a trajectory
    that only shows tool calls with no verdict at the end would hide the
    one thing this project's whole approach is actually about.
    """
    lines = [
        f"# Trajectory: {case_id}",
        "",
        "## Agent instructions (system prompt)",
        "",
        "```",
        instructions.strip(),
        "```",
        "",
        "## Initial prompt",
        "",
        "```",
        initial_prompt.strip(),
        "```",
        "",
    ]
    for i, messages in enumerate(attempts):
        heading = f"## Attempt {i + 1}" if len(attempts) > 1 else "## Run"
        lines.append(heading)
        lines.append("")
        for message in messages:
            rendered = _render_message(message)
            if rendered:
                lines.extend(rendered)
                lines.append("")
        if feedback_between_attempts and i < len(feedback_between_attempts):
            lines.append(f"### Verification feedback fed back before attempt {i + 2}")
            lines.append("")
            lines.append("```")
            lines.append(feedback_between_attempts[i].strip())
            lines.append("```")
            lines.append("")
    if final_verdict:
        lines.append("## Verification (closed the loop)")
        lines.append("")
        lines.append("```")
        lines.append(final_verdict.strip())
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


def save(
    case_id: str,
    instructions: str,
    initial_prompt: str,
    attempts: list[list[Any]],
    out_dir: Path,
    feedback_between_attempts: list[str] | None = None,
    final_verdict: str | None = None,
) -> tuple[Path, Path]:
    """Writes both required artifacts and returns their paths: a .jsonl
    (every attempt's raw messages, each tagged with its attempt index --
    the mechanical trace) and a .md (the human-readable walkthrough).
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = out_dir / f"{case_id}.jsonl"
    md_path = out_dir / f"{case_id}.md"

    with open(jsonl_path, "w", encoding="utf-8") as f:
        for attempt_idx, messages in enumerate(attempts):
            for message in messages:
                record = _to_jsonable(message)
                record["attempt"] = attempt_idx
                f.write(json.dumps(record, default=str) + "\n")
        if final_verdict:
            f.write(json.dumps({"type": "VerificationReport", "text": final_verdict}, default=str) + "\n")

    md_path.write_text(
        render_markdown(case_id, instructions, initial_prompt, attempts, feedback_between_attempts, final_verdict),
        encoding="utf-8",
    )
    return jsonl_path, md_path
