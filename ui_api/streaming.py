"""SSE formatting + OpenAI Agents SDK stream-event translation.

Pure helpers (no app/service state) used by `orchestrator_service.stream_orchestrator_chat`
to turn `Runner.run_streamed(...).stream_events()` into the UI's SSE contract:

    event: token        data: { delta }
    event: tool_call    data: { id, tool, label, args }
    event: tool_result  data: { id, tool, status, summary }
    event: handoff      data: { to }
    event: evidence     data: { id, kind, title, payload }
    event: usage        data: { round_trips, tokens, by_agent }
    event: done         data: { final, session_id, run_id, next_steps, metrics }
    event: error        data: { message }

Step 1 of the UI redesign (see docs/UI_REDESIGN_PLAN.md). The translators are
defensive about SDK event/item shapes — they reach for attributes with getattr
fallbacks rather than importing internal item classes.
"""

from __future__ import annotations

import json
from typing import Any

# Mirrors AGENT_LABELS in ui_web/src/App.jsx so Trace/Evidence read consistently.
_TOOL_LABEL = {
    "analyze_slow_queries": "Slow Query Analysis",
    "analyze_running_queries": "Running Query Analysis",
    "perform_incident_triage": "Incident Triage",
    "check_replication_health": "Replication Health",
    "execute_database_query": "Database Inspector",
    "get_mariadb_cloud_observability_snapshot": "MariaDB Cloud Observability",
    "query_mariadb_cloud_observability_metrics": "MariaDB Cloud Metrics Query",
}

# Coarse evidence-card kind per orchestrator tool. Richer per-probe kinds
# (explain/processlist/perf_schema rows) come when the specialist tools return
# structured rows the bridge can serialize directly (UI_REDESIGN_PLAN.md §5).
_TOOL_EVIDENCE_KIND = {
    "analyze_slow_queries": "slow_log",
    "analyze_running_queries": "processlist",
    "perform_incident_triage": "triage",
    "check_replication_health": "replication",
    "execute_database_query": "sql",
    "get_mariadb_cloud_observability_snapshot": "observability",
    "query_mariadb_cloud_observability_metrics": "observability",
}


def sse(event: str, data: Any) -> str:
    """Format a single Server-Sent Event frame."""
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


# --- raw token deltas -------------------------------------------------------

def text_delta(raw_event: Any) -> str | None:
    """Extract an assistant text delta from a raw_response_event, if present."""
    data = getattr(raw_event, "data", None)
    if data is None:
        return None
    if getattr(data, "type", None) == "response.output_text.delta":
        delta = getattr(data, "delta", None)
        return delta if isinstance(delta, str) and delta else None
    return None


# --- run items (tool calls, outputs, handoffs) ------------------------------

def tool_call_payload(item: Any) -> dict[str, Any]:
    raw = getattr(item, "raw_item", None)
    name = getattr(raw, "name", None) or "tool"
    args = getattr(raw, "arguments", None)  # JSON string per the SDK
    call_id = getattr(raw, "call_id", None) or getattr(raw, "id", None)
    return {
        "id": call_id,
        "tool": name,
        "label": _TOOL_LABEL.get(name, name),
        "args": _maybe_parse_json(args),
    }


def tool_output_payload(item: Any, tool_by_call: dict[str, str]) -> dict[str, Any]:
    raw = getattr(item, "raw_item", None)
    call_id = raw.get("call_id") if isinstance(raw, dict) else getattr(raw, "call_id", None)
    output = getattr(item, "output", None)
    tool = tool_by_call.get(call_id or "", "tool")

    status = "done"
    summary: Any = output
    if isinstance(output, dict):
        if output.get("success") is False:
            status = "failed"
        summary = output.get("report") or output.get("error") or output
    return {
        "id": call_id,
        "tool": tool,
        "label": _TOOL_LABEL.get(tool, tool),
        "status": status,
        "summary": _truncate(summary),
    }


def evidence_payload(item: Any, tool_by_call: dict[str, str]) -> dict[str, Any] | None:
    """Emit an evidence card when a tool output carries a showable report."""
    raw = getattr(item, "raw_item", None)
    call_id = raw.get("call_id") if isinstance(raw, dict) else getattr(raw, "call_id", None)
    output = getattr(item, "output", None)
    tool = tool_by_call.get(call_id or "", "")

    if not isinstance(output, dict) or "report" not in output:
        return None
    return {
        "id": call_id,
        "kind": _TOOL_EVIDENCE_KIND.get(tool, "evidence"),
        "title": _TOOL_LABEL.get(tool, output.get("agent") or tool or "Evidence"),
        "payload": _truncate(output.get("report")),
    }


def handoff_payload(item: Any) -> dict[str, Any]:
    target = getattr(item, "target_agent", None) or getattr(item, "agent", None)
    name = getattr(target, "name", None) if target is not None else None
    return {"to": name or "specialist"}


# --- helpers ----------------------------------------------------------------

def _maybe_parse_json(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return value
    return value


def _truncate(value: Any, limit: int = 6000) -> Any:
    if isinstance(value, str) and len(value) > limit:
        return value[:limit] + "\n…(truncated)"
    return value
