"""Tests flakedoctor.trajectory against synthetic message objects -- this
is the project's own rendering code, not a benchmark fixture, so real SDK
message shapes are constructed by hand rather than captured from a live
run (that would need an API call).
"""
from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)

from flakedoctor.trajectory import save


def _assistant_tool_call(tool_use_id, name, tool_input):
    return AssistantMessage(
        content=[ToolUseBlock(id=tool_use_id, name=name, input=tool_input)],
        model="claude-sonnet-5", parent_tool_use_id=None, error=None, usage={},
        message_id="m", stop_reason=None, session_id="s", uuid="u",
    )


def _tool_result(tool_use_id, content):
    return UserMessage(
        content=[ToolResultBlock(tool_use_id=tool_use_id, content=content, is_error=None)],
        uuid="u", parent_tool_use_id=None, tool_use_result=None, origin=None,
    )


def _assistant_text(text):
    return AssistantMessage(
        content=[TextBlock(text=text)],
        model="claude-sonnet-5", parent_tool_use_id=None, error=None, usage={},
        message_id="m", stop_reason=None, session_id="s", uuid="u",
    )


def _result(num_turns, cost_usd):
    return ResultMessage(
        subtype="success", duration_ms=1, duration_api_ms=1, is_error=False,
        num_turns=num_turns, session_id="s", stop_reason="end_turn", total_cost_usd=cost_usd,
        usage={}, result="ok", structured_output=None, model_usage={}, permission_denials=[],
        deferred_tool_use=None, errors=None, api_error_status=None, uuid="u",
        terminal_reason="completed", origin=None,
    )


def test_single_attempt_round_trips_through_jsonl_and_markdown(tmp_path):
    attempt = [
        _assistant_tool_call("t1", "Read", {"file_path": "tests/test_x.py"}),
        _tool_result("t1", "1\tdef test_x(): ..."),
        _assistant_text("Diagnosed and fixed the flake."),
        _result(num_turns=3, cost_usd=0.05),
    ]

    jsonl_path, md_path = save(
        case_id="fake_case",
        instructions="You are a careful software engineer...",
        initial_prompt="The test tests/test_x.py::test_x is flaky...",
        attempts=[attempt],
        out_dir=tmp_path,
    )

    jsonl_lines = jsonl_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(jsonl_lines) == len(attempt)
    import json
    records = [json.loads(line) for line in jsonl_lines]
    assert [r["attempt"] for r in records] == [0, 0, 0, 0]
    assert records[0]["type"] == "AssistantMessage"
    assert records[0]["content"][0]["name"] == "Read"

    markdown = md_path.read_text(encoding="utf-8")
    assert "Diagnosed and fixed the flake." in markdown
    assert "**Tool call** `Read`" in markdown
    assert "1\tdef test_x(): ..." in markdown
    assert "cost $0.0500" in markdown


def test_retry_feedback_appears_between_attempts(tmp_path):
    attempt1 = [_assistant_text("First try."), _result(num_turns=2, cost_usd=0.02)]
    attempt2 = [_assistant_text("Adjusted based on feedback."), _result(num_turns=1, cost_usd=0.01)]

    _, md_path = save(
        case_id="fake_retry_case",
        instructions="...",
        initial_prompt="...",
        attempts=[attempt1, attempt2],
        out_dir=tmp_path,
        feedback_between_attempts=["[FAIL] sensitivity: mutant not caught"],
    )

    markdown = md_path.read_text(encoding="utf-8")
    # The feedback must appear after attempt 1's content and before attempt 2's.
    first_try_pos = markdown.index("First try.")
    feedback_pos = markdown.index("mutant not caught")
    second_try_pos = markdown.index("Adjusted based on feedback.")
    assert first_try_pos < feedback_pos < second_try_pos
    assert "## Attempt 1" in markdown
    assert "## Attempt 2" in markdown


def test_long_tool_result_is_truncated(tmp_path):
    huge_output = "x" * 5000
    attempt = [_tool_result("t1", huge_output)]

    _, md_path = save(
        case_id="fake_long_output",
        instructions="...",
        initial_prompt="...",
        attempts=[attempt],
        out_dir=tmp_path,
    )

    markdown = md_path.read_text(encoding="utf-8")
    assert "truncated" in markdown
    assert len(markdown) < len(huge_output)
