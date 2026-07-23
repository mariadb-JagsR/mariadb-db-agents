from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import dotenv_values, load_dotenv

from .paths import ENV_PATH, PROFILES_PATH, SESSIONS_PATH, TOGGLES_PATH, UI_DATA_DIR
from .schemas import AgentToggleState, CreateProfileRequest, DBProfile, SessionData, SessionMessage, UpdateProfileRequest
from .store import load_json, save_json_atomic


REQUIRED_KEYS = ["OPENAI_API_KEY", "DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_DATABASE"]
OPTIONAL_KEYS = [
    "OPENAI_MODEL",
    "MARIADB_CLOUD_API_KEY",
    "MARIADB_CLOUD_SERVICE_ID",
    "MARIADB_CLOUD_LOG_API_URL",
]
PROFILE_ENV_KEYS = ["DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_DATABASE"]
SECRET_KEYS = {"OPENAI_API_KEY", "DB_PASSWORD", "MARIADB_CLOUD_API_KEY"}
SECRET_MASK = "********"
DEFAULT_TOGGLES = AgentToggleState().model_dump()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _read_env_map() -> dict[str, str]:
    if not ENV_PATH.exists():
        return {}
    parsed = dotenv_values(ENV_PATH)
    return {k: str(v) for k, v in parsed.items() if v is not None}


def _safe_quote(value: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_./:@-]+", value):
        return value
    escaped = value.replace('"', '\\"')
    return f'"{escaped}"'


def update_env_values(values: dict[str, str]) -> None:
    current = _read_env_map()
    current.update(values)

    backup_path = ENV_PATH.with_name(f"{ENV_PATH.name}.bak")
    if ENV_PATH.exists():
        backup_path.write_text(ENV_PATH.read_text(encoding="utf-8"), encoding="utf-8")

    lines = [f"{key}={_safe_quote(val)}" for key, val in sorted(current.items())]
    body = "\n".join(lines) + "\n"
    temp = ENV_PATH.with_suffix(".env.tmp")
    temp.write_text(body, encoding="utf-8")
    temp.replace(ENV_PATH)
    # `common.config` only runs load_dotenv() once at import. Keep this process in sync with the file
    # so profile activation and Config "Save" apply without restarting the server.
    load_dotenv(ENV_PATH, override=True)


def get_env_values(redact_secrets: bool = True) -> dict[str, str]:
    current = _read_env_map()
    keys = REQUIRED_KEYS + OPTIONAL_KEYS
    result: dict[str, str] = {}
    for key in keys:
        value = current.get(key, "")
        if redact_secrets and key in SECRET_KEYS and value:
            result[key] = SECRET_MASK
        else:
            result[key] = value
    return result


def get_env_status() -> tuple[dict[str, bool], dict[str, bool]]:
    current = _read_env_map()
    required = {key: bool(current.get(key)) for key in REQUIRED_KEYS}
    optional = {key: bool(current.get(key)) for key in OPTIONAL_KEYS}
    return required, optional


def _default_profiles_state() -> dict[str, Any]:
    return {"active_profile_id": None, "profiles": []}


def _load_profiles_state() -> dict[str, Any]:
    return load_json(PROFILES_PATH, _default_profiles_state())


def _save_profiles_state(state: dict[str, Any]) -> None:
    save_json_atomic(PROFILES_PATH, state)


def list_profiles() -> dict[str, Any]:
    return _load_profiles_state()


def list_profiles_redacted() -> dict[str, Any]:
    state = _load_profiles_state()
    redacted_profiles = []
    for profile in state.get("profiles", []):
        item = dict(profile)
        if item.get("password"):
            item["password"] = SECRET_MASK
        redacted_profiles.append(item)
    return {"active_profile_id": state.get("active_profile_id"), "profiles": redacted_profiles}


def redact_profile(profile: DBProfile) -> dict[str, Any]:
    payload = profile.model_dump(mode="json")
    if payload.get("password"):
        payload["password"] = SECRET_MASK
    return payload


def create_profile(request: CreateProfileRequest) -> DBProfile:
    state = _load_profiles_state()
    now = _now()
    profile = DBProfile(
        id=str(uuid.uuid4()),
        name=request.name,
        host=request.host,
        port=request.port,
        user=request.user,
        password=request.password,
        database=request.database,
        created_at=now,
        updated_at=now,
    )
    state["profiles"].append(profile.model_dump(mode="json"))
    if not state["active_profile_id"]:
        state["active_profile_id"] = profile.id
        activate_profile(profile.id, state=state)
    _save_profiles_state(state)
    return profile


def update_profile(profile_id: str, request: UpdateProfileRequest) -> DBProfile:
    state = _load_profiles_state()
    profiles = state["profiles"]
    for idx, raw in enumerate(profiles):
        if raw["id"] == profile_id:
            merged = {**raw, **request.model_dump(exclude_none=True), "updated_at": _now().isoformat()}
            profile = DBProfile(**merged)
            profiles[idx] = profile.model_dump(mode="json")
            _save_profiles_state(state)
            if state.get("active_profile_id") == profile_id:
                activate_profile(profile_id, state=state)
            return profile
    raise KeyError(f"Profile not found: {profile_id}")


def delete_profile(profile_id: str) -> None:
    state = _load_profiles_state()
    profiles = [p for p in state["profiles"] if p["id"] != profile_id]
    if len(profiles) == len(state["profiles"]):
        raise KeyError(f"Profile not found: {profile_id}")
    state["profiles"] = profiles
    if state.get("active_profile_id") == profile_id:
        state["active_profile_id"] = profiles[0]["id"] if profiles else None
        if state["active_profile_id"]:
            activate_profile(state["active_profile_id"], state=state)
    _save_profiles_state(state)


def activate_profile(profile_id: str, state: dict[str, Any] | None = None) -> None:
    state = state or _load_profiles_state()
    profile_raw = next((p for p in state["profiles"] if p["id"] == profile_id), None)
    if not profile_raw:
        raise KeyError(f"Profile not found: {profile_id}")

    env_update = {
        "DB_HOST": profile_raw["host"],
        "DB_PORT": str(profile_raw["port"]),
        "DB_USER": profile_raw["user"],
        "DB_PASSWORD": profile_raw["password"],
        "DB_DATABASE": profile_raw["database"],
    }
    update_env_values(env_update)
    state["active_profile_id"] = profile_id
    _save_profiles_state(state)


def get_agent_toggles() -> AgentToggleState:
    payload = load_json(TOGGLES_PATH, {"toggles": DEFAULT_TOGGLES})
    return AgentToggleState(**payload.get("toggles", DEFAULT_TOGGLES))


def set_agent_toggles(toggles: AgentToggleState) -> AgentToggleState:
    save_json_atomic(TOGGLES_PATH, {"toggles": toggles.model_dump()})
    return toggles


def set_default_toggles() -> AgentToggleState:
    defaults = AgentToggleState()
    return set_agent_toggles(defaults)


def list_sessions() -> list[dict[str, Any]]:
    payload = load_json(SESSIONS_PATH, {"sessions": []})
    return payload["sessions"]


def get_session_by_id(session_id: str) -> dict[str, Any] | None:
    payload = load_json(SESSIONS_PATH, {"sessions": []})
    return next((session for session in payload.get("sessions", []) if session.get("id") == session_id), None)


def delete_session(session_id: str) -> None:
    payload = load_json(SESSIONS_PATH, {"sessions": []})
    sessions = payload.get("sessions", [])
    filtered = [session for session in sessions if session.get("id") != session_id]
    if len(filtered) == len(sessions):
        raise KeyError(f"Session not found: {session_id}")
    payload["sessions"] = filtered
    save_json_atomic(SESSIONS_PATH, payload)


def append_session_message(
    session_id: str,
    role: str,
    content: str,
    title: str | None = None,
) -> SessionData:
    payload = load_json(SESSIONS_PATH, {"sessions": []})
    now = _now()
    existing = next((s for s in payload["sessions"] if s["id"] == session_id), None)
    if not existing:
        existing = SessionData(
            id=session_id,
            title=title or "New Session",
            messages=[],
            created_at=now,
            updated_at=now,
        ).model_dump(mode="json")
        payload["sessions"].append(existing)

    existing["messages"].append(SessionMessage(role=role, content=content, created_at=now).model_dump(mode="json"))
    existing["updated_at"] = now.isoformat()
    if title and existing["title"] == "New Session":
        existing["title"] = title

    save_json_atomic(SESSIONS_PATH, payload)
    return SessionData(**existing)


def ensure_ui_data_dir() -> None:
    Path(UI_DATA_DIR).mkdir(parents=True, exist_ok=True)

