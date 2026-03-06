from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

from agents import Runner, set_default_openai_key

from ..common.config import OpenAIConfig
from ..common.observability import InteractionMetrics, get_tracker
from ..orchestrator.agent import create_orchestrator_agent
from .config_service import append_session_message, get_agent_toggles, get_session_by_id
from .next_steps import extract_next_steps
from .paths import RUN_HISTORY_PATH
from .progress import reset_progress_callback, set_progress_callback
from .store import load_json, save_json_atomic


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _record_run(run_payload: dict[str, Any]) -> None:
    state = load_json(RUN_HISTORY_PATH, {"runs": []})
    state["runs"].append(run_payload)
    state["runs"] = state["runs"][-200:]
    save_json_atomic(RUN_HISTORY_PATH, state)


def _latest_interaction(before_count: int) -> InteractionMetrics | None:
    tracker = get_tracker()
    if len(tracker.interactions) <= before_count:
        return None
    return tracker.interactions[-1]


_chat_runs: dict[str, dict[str, Any]] = {}
_chat_runs_lock = asyncio.Lock()


def _event(message: str) -> dict[str, Any]:
    return {"timestamp": _now().isoformat(), "message": message}


async def _set_run_state(run_id: str, **updates: Any) -> None:
    async with _chat_runs_lock:
        if run_id in _chat_runs:
            _chat_runs[run_id].update(updates)


async def _add_run_event(run_id: str, message: str) -> None:
    async with _chat_runs_lock:
        if run_id not in _chat_runs:
            return
        events = _chat_runs[run_id].setdefault("events", [])
        events.append(_event(message))
        _chat_runs[run_id]["events"] = events[-60:]


async def _get_run(run_id: str) -> dict[str, Any] | None:
    async with _chat_runs_lock:
        payload = _chat_runs.get(run_id)
        return dict(payload) if payload else None


def _build_prompt_with_history(session_id: str | None, message: str) -> str:
    """
    Construct a conversation-aware prompt from recent session history.
    """
    if not session_id:
        return message

    session = get_session_by_id(session_id)
    if not session:
        return message

    history = session.get("messages", [])
    if not history:
        return message

    # Keep context bounded to avoid ballooning tokens.
    recent_window = 12
    recent = history[-recent_window:]
    older = history[:-recent_window]
    lines = [
        "Conversation context from this chat session:",
        "(Use this as prior turns for continuity.)",
    ]
    if older:
        # Summarize older turns in a compact, bounded format.
        # We keep only a short prefix per turn to preserve intent without large token cost.
        summary_parts: list[str] = []
        for item in older[-20:]:
            role = item.get("role", "user")
            content = str(item.get("content", "")).strip().replace("\n", " ")
            if not content:
                continue
            short = content[:160] + ("..." if len(content) > 160 else "")
            summary_parts.append(f"{role}:{short}")
        if summary_parts:
            lines.append("Earlier context summary:")
            lines.append(" | ".join(summary_parts))

    for item in recent:
        role = item.get("role", "user")
        content = str(item.get("content", "")).strip()
        if not content:
            continue
        lines.append(f"{role.upper()}: {content}")

    lines.append("USER (current question):")
    lines.append(message)
    return "\n\n".join(lines)


async def run_orchestrator_chat(
    message: str,
    max_turns: int,
    session_id: str | None = None,
) -> dict[str, Any]:
    return await _run_orchestrator_chat_internal(
        message=message,
        max_turns=max_turns,
        session_id=session_id,
        run_id=None,
    )


async def _run_orchestrator_chat_internal(
    message: str,
    max_turns: int,
    session_id: str | None,
    run_id: str | None,
) -> dict[str, Any]:
    cfg = OpenAIConfig.from_env()
    set_default_openai_key(cfg.api_key)
    toggles = get_agent_toggles().model_dump()
    enabled_tools = {tool_name for tool_name, enabled in toggles.items() if enabled}
    effective_input = _build_prompt_with_history(session_id, message)
    if run_id:
        await _add_run_event(run_id, "Preparing context and planning investigation...")

    tracker = get_tracker()
    before_count = len(tracker.interactions)
    agent = create_orchestrator_agent(enabled_tools=enabled_tools)
    token = None
    if run_id:
        token = set_progress_callback(lambda msg: asyncio.create_task(_add_run_event(run_id, msg)))
    try:
        result = await Runner.run(agent, effective_input, max_turns=max_turns)
    finally:
        if token is not None:
            reset_progress_callback(token)

    if run_id:
        await _add_run_event(run_id, "Finalizing recommendations...")
    metrics = tracker.track_interaction(user_input=message, result=result, is_orchestrator=True)

    created_at = _now()
    response_text = result.final_output or "No output generated."
    next_steps = extract_next_steps(response_text)
    resolved_session_id = session_id or str(uuid.uuid4())
    run_id = str(uuid.uuid4())

    append_session_message(resolved_session_id, "user", message, title=message[:60])
    session = append_session_message(resolved_session_id, "assistant", response_text)

    totals = metrics.get_total_with_sub_agents()
    _record_run(
        {
            "run_id": run_id,
            "session_id": resolved_session_id,
            "created_at": created_at.isoformat(),
            "message": message[:500],
            "metrics": totals,
            "next_steps": next_steps,
            "tool_toggles": toggles,
        }
    )

    latest = _latest_interaction(before_count)
    per_request_usage = latest.per_request_usage if latest else []
    return {
        "response": response_text,
        "next_steps": next_steps,
        "metrics": {
            **totals,
            "per_request_usage": per_request_usage,
        },
        "session_id": resolved_session_id,
        "run_id": run_id,
        "created_at": created_at,
        "session": session.model_dump(mode="json"),
    }


async def start_orchestrator_chat_run(
    message: str,
    max_turns: int,
    session_id: str | None = None,
) -> str:
    run_id = str(uuid.uuid4())
    async with _chat_runs_lock:
        _chat_runs[run_id] = {
            "run_id": run_id,
            "status": "queued",
            "created_at": _now().isoformat(),
            "events": [_event("Queued request...")],
            "result": None,
            "error": None,
        }

    async def _runner() -> None:
        await _set_run_state(run_id, status="running")
        await _add_run_event(run_id, "Starting analysis...")
        try:
            result = await _run_orchestrator_chat_internal(
                message=message,
                max_turns=max_turns,
                session_id=session_id,
                run_id=run_id,
            )
            await _set_run_state(run_id, status="completed", result=result)
            await _add_run_event(run_id, "Completed.")
        except Exception as exc:
            await _set_run_state(run_id, status="failed", error=str(exc))
            await _add_run_event(run_id, "Failed.")

    asyncio.create_task(_runner())
    return run_id


async def get_orchestrator_chat_run(run_id: str) -> dict[str, Any] | None:
    return await _get_run(run_id)

