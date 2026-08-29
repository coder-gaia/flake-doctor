"""FastAPI app: a case picker, a Run button, and a live log, backed by
the exact same functions the CLI calls (flakedoctor.agent._run_once /
_run_with_verification). See flakedoctor/web/__init__.py for what this is
and is not.

Run with `python -m flakedoctor.web` from the repo root and open
http://127.0.0.1:8000.
"""
from __future__ import annotations

import asyncio
import json
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from claude_agent_sdk import AssistantMessage, TextBlock, ToolResultBlock, ToolUseBlock, UserMessage
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from baselines.single_prompt import copy_case_without_answer_key
# _run_once/_run_with_verification (leading underscore) are the coroutines
# themselves; the public wrappers of the same name without it
# (run_agent_on_case, fix_case_with_verification, ...) call
# asyncio.run(...) internally, which cannot be awaited from inside an
# already-running event loop -- exactly the situation an async route
# handler is in. Importing the "private" coroutines directly is
# deliberate, not an oversight.
from flakedoctor.agent import (
    AttemptEvent,
    DEFAULT_MAX_RETRIES,
    DEFAULT_MAX_TURNS,
    DEFAULT_MAX_TURNS_WITH_RETRY,
    _run_once,
    _run_with_verification,
    describe_tool_result,
    describe_tool_use,
)

# verify_reruns is fixed, not a UI knob: matches the CLI's own --verify
# default (30) so a run started from the browser is directly comparable
# to one started from the terminal, per REPRODUCTION.md.
VERIFY_RERUNS = 30

STATIC_DIR = Path(__file__).parent / "static"
CASE_ROOTS = ("benchmark/cases", "case-studies")

app = FastAPI(title="Flake Doctor")


def discover_cases() -> list[dict]:
    """Scans the same two directories the rest of the project already
    treats as the source of truth for cases (benchmark/cases for the 14
    designed cases, case-studies for real-world ones), relative to the
    current working directory -- same convention the CLI uses for its
    case_dir argument, so this only ever finds cases a clean checkout
    already ships, never an arbitrary path.
    """
    cases = []
    for root in CASE_ROOTS:
        base = Path(root)
        if not base.is_dir():
            continue
        for case_dir in sorted(p for p in base.iterdir() if p.is_dir()):
            case_yaml = case_dir / "case.yaml"
            if not case_yaml.is_file():
                continue
            try:
                data = yaml.safe_load(case_yaml.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError:
                continue
            cases.append({
                "id": data.get("id", case_dir.name),
                "dir": str(case_dir).replace("\\", "/"),
                "category": data.get("category", ""),
                "target_test": data.get("target_test", ""),
                "description": " ".join((data.get("description") or "").split()),
                "source": data.get("source"),
            })
    return cases


@dataclass
class RunState:
    queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    task: asyncio.Task | None = None


RUNS: dict[str, RunState] = {}


def _format_event(message: Any, tool_names_by_id: dict[str, str], candidate_dir: Path) -> dict | None:
    """Mirrors flakedoctor.agent._print_trajectory's logic exactly (same
    tool_names_by_id bookkeeping, same describe_tool_use/describe_tool_result
    calls) so the browser's live log and the CLI's --verbose output never
    drift into two different stories about the same run.
    """
    if isinstance(message, AttemptEvent):
        if message.kind == "attempt_start":
            return {"kind": "attempt_start", "attempt": message.attempt}
        report = message.report
        return {
            "kind": "verification",
            "attempt": message.attempt,
            "passed": report.all_passed,
            "gates": [{"name": g.name, "passed": g.passed, "detail": g.detail} for g in report.gates],
        }
    if isinstance(message, AssistantMessage):
        items = []
        for block in message.content:
            if isinstance(block, ToolUseBlock):
                tool_names_by_id[block.id] = block.name
                items.append({"kind": "tool_use", "text": describe_tool_use(block, candidate_dir)})
            elif isinstance(block, TextBlock) and block.text.strip():
                items.append({"kind": "diagnosis", "text": block.text.strip()})
        return {"kind": "batch", "items": items} if items else None
    if isinstance(message, UserMessage):
        items = []
        for block in message.content:
            if isinstance(block, ToolResultBlock):
                line = describe_tool_result(tool_names_by_id.get(block.tool_use_id), block.content)
                if line:
                    items.append({"kind": "tool_result", "text": line})
        return {"kind": "batch", "items": items} if items else None
    return None


async def _execute_run(run_id: str, case_dir: Path, target_test: str, verify: bool) -> None:
    """Runs in the background (see create_run's asyncio.create_task) and
    talks to the run's own queue only -- the SSE endpoint below is the
    only reader, so this never touches the HTTP layer directly.
    """
    queue = RUNS[run_id].queue
    tool_names_by_id: dict[str, str] = {}
    candidate_box: dict[str, Path] = {}
    file_part, _ = target_test.split("::", 1)

    def on_message(msg: Any) -> None:
        event = _format_event(msg, tool_names_by_id, candidate_box["candidate"])
        if event:
            queue.put_nowait(("event", event))

    try:
        with tempfile.TemporaryDirectory(prefix="flakedoctor_web_") as tmp:
            candidate = copy_case_without_answer_key(case_dir, Path(tmp) / "candidate")
            candidate_box["candidate"] = candidate

            if verify:
                result = await _run_with_verification(
                    case_dir, candidate, target_test,
                    DEFAULT_MAX_TURNS_WITH_RETRY, DEFAULT_MAX_RETRIES, VERIFY_RERUNS, on_message,
                )
                queue.put_nowait(("done", {
                    "verdict": "PASS" if result.verification.all_passed else "FAIL",
                    "attempts": result.attempts,
                    "cost_usd": round(result.total_cost_usd, 4),
                    "gates": [
                        {"name": g.name, "passed": g.passed, "detail": g.detail}
                        for g in result.verification.gates
                    ],
                    "file_path": file_part,
                    "file_content": (candidate / file_part).read_text(encoding="utf-8"),
                }))
            else:
                run = await _run_once(candidate, target_test, DEFAULT_MAX_TURNS, on_message)
                queue.put_nowait(("done", {
                    "verdict": None,
                    "attempts": 1,
                    "cost_usd": round(run.cost_usd, 4),
                    "gates": None,
                    "file_path": file_part,
                    "file_content": (candidate / file_part).read_text(encoding="utf-8"),
                    "final_text": run.final_text,
                }))
    except Exception as exc:  # surfaced to the browser, not swallowed -- see the UI's error banner
        queue.put_nowait(("error", {"message": str(exc)}))
    finally:
        queue.put_nowait(("end", {}))


class RunRequest(BaseModel):
    case_dir: str
    target_test: str = ""
    verify: bool = True


@app.get("/api/cases")
async def list_cases() -> list[dict]:
    return discover_cases()


@app.post("/api/runs")
async def create_run(req: RunRequest) -> dict:
    known = {c["dir"]: c for c in discover_cases()}
    case = known.get(req.case_dir.replace("\\", "/"))
    if case is None:
        # Only ever a directory discover_cases() itself found, never an
        # arbitrary path -- this is a local dev tool with one user, but
        # there is no reason to let a request pick a pytest target outside
        # the project's own known cases.
        raise HTTPException(status_code=400, detail=f"unknown case: {req.case_dir}")
    target_test = req.target_test.strip() or case["target_test"]
    if not target_test:
        raise HTTPException(status_code=400, detail="no target_test given, and none in the case's case.yaml")

    run_id = uuid.uuid4().hex[:12]
    state = RunState()
    RUNS[run_id] = state
    # Keep the reference on RunState: asyncio warns that a task with no
    # referrer can be garbage-collected mid-run.
    state.task = asyncio.create_task(_execute_run(run_id, Path(case["dir"]), target_test, req.verify))
    return {"run_id": run_id}


@app.get("/api/runs/{run_id}/events")
async def run_events(run_id: str):
    state = RUNS.get(run_id)
    if state is None:
        raise HTTPException(status_code=404, detail="unknown run_id (already finished and cleaned up?)")

    async def gen():
        try:
            while True:
                kind, payload = await state.queue.get()
                if kind == "end":
                    yield "event: end\ndata: {}\n\n"
                    break
                yield f"event: {kind}\ndata: {json.dumps(payload)}\n\n"
        finally:
            # Known simplification: a run whose SSE connection never opens
            # (tab closed before it could) leaks this dict entry for the
            # life of the process. Acceptable for a local, single-user dev
            # tool restarted between sessions; would need a TTL sweep in
            # anything longer-lived.
            RUNS.pop(run_id, None)

    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")
