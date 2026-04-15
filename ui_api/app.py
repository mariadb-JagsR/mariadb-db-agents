from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from ..common.observability import get_tracker
from .config_service import (
    activate_profile,
    create_profile,
    delete_session,
    delete_profile,
    ensure_ui_data_dir,
    get_agent_toggles,
    get_env_status,
    get_env_values,
    list_profiles,
    list_profiles_redacted,
    list_sessions,
    redact_profile,
    set_agent_toggles,
    set_default_toggles,
    update_env_values,
    update_profile,
)
from .orchestrator_service import (
    get_orchestrator_chat_run,
    run_orchestrator_chat,
    start_orchestrator_chat_run,
)
from .paths import RUN_HISTORY_PATH
from .schemas import (
    AgentToggleResponse,
    AgentToggleState,
    ChatRequest,
    ChatResponse,
    CreateProfileRequest,
    EnvValuesResponse,
    EnvStatusResponse,
    EnvUpdateRequest,
    UpdateProfileRequest,
)
from .store import load_json


app = FastAPI(title="MariaDB + MySQL Root-Cause Insight API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    ensure_ui_data_dir()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat/orchestrator", response_model=ChatResponse)
async def chat_orchestrator(request: ChatRequest) -> dict[str, Any]:
    try:
        return await run_orchestrator_chat(
            message=request.message,
            max_turns=request.max_turns,
            session_id=request.session_id,
        )
    except Exception as exc:  # pragma: no cover - exact SDK failures vary by environment.
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/chat/orchestrator/run")
async def start_chat_orchestrator_run(request: ChatRequest) -> dict[str, Any]:
    run_id = await start_orchestrator_chat_run(
        message=request.message,
        max_turns=request.max_turns,
        session_id=request.session_id,
    )
    return {"run_id": run_id}


@app.get("/chat/orchestrator/run/{run_id}")
async def get_chat_orchestrator_run(run_id: str) -> dict[str, Any]:
    run = await get_orchestrator_chat_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    return run


@app.get("/config/status", response_model=EnvStatusResponse)
def config_status() -> dict[str, Any]:
    required, optional = get_env_status()
    profiles = list_profiles()
    return {
        "required": required,
        "optional": optional,
        "current_profile_id": profiles.get("active_profile_id"),
    }


@app.get("/config/env-values", response_model=EnvValuesResponse)
def config_env_values() -> dict[str, Any]:
    return {"values": get_env_values(redact_secrets=True)}


@app.put("/config/env")
def update_env(request: EnvUpdateRequest) -> dict[str, str]:
    update_env_values(request.values)
    return {"status": "updated"}


@app.get("/profiles")
def get_profiles() -> dict[str, Any]:
    return list_profiles_redacted()


@app.post("/profiles")
def post_profile(request: CreateProfileRequest) -> dict[str, Any]:
    profile = create_profile(request)
    return {"profile": redact_profile(profile)}


@app.put("/profiles/{profile_id}")
def put_profile(profile_id: str, request: UpdateProfileRequest) -> dict[str, Any]:
    try:
        profile = update_profile(profile_id, request)
        return {"profile": redact_profile(profile)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.delete("/profiles/{profile_id}")
def remove_profile(profile_id: str) -> dict[str, str]:
    try:
        delete_profile(profile_id)
        return {"status": "deleted"}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.put("/profiles/{profile_id}/activate")
def set_active_profile(profile_id: str) -> dict[str, str]:
    try:
        activate_profile(profile_id)
        return {"status": "activated"}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/agents/toggles", response_model=AgentToggleResponse)
def get_toggles() -> dict[str, Any]:
    return {"toggles": get_agent_toggles()}


@app.put("/agents/toggles", response_model=AgentToggleResponse)
def put_toggles(request: AgentToggleState) -> dict[str, Any]:
    toggles = set_agent_toggles(request)
    return {"toggles": toggles}


@app.post("/agents/toggles/defaults", response_model=AgentToggleResponse)
def reset_toggles() -> dict[str, Any]:
    toggles = set_default_toggles()
    return {"toggles": toggles}


@app.get("/sessions")
def get_sessions() -> dict[str, Any]:
    return {"sessions": list_sessions()}


@app.delete("/sessions/{session_id}")
def remove_session(session_id: str) -> dict[str, str]:
    try:
        delete_session(session_id)
        return {"status": "deleted"}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/observability/summary")
def observability_summary() -> dict[str, Any]:
    tracker = get_tracker()
    history = load_json(RUN_HISTORY_PATH, {"runs": []})
    return {
        "summary": tracker.get_summary(),
        "recent_runs": history["runs"][-25:],
    }

