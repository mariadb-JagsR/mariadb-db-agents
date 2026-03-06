from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    max_turns: int = Field(default=30, ge=1, le=100)
    profile_id: str | None = None
    session_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    next_steps: list[str]
    metrics: dict[str, Any]
    session_id: str
    run_id: str
    created_at: datetime


class EnvUpdateRequest(BaseModel):
    values: dict[str, str]


class EnvStatusResponse(BaseModel):
    required: dict[str, bool]
    optional: dict[str, bool]
    current_profile_id: str | None


class EnvValuesResponse(BaseModel):
    values: dict[str, str]


class DBProfile(BaseModel):
    id: str
    name: str
    host: str
    port: int = 3306
    user: str
    password: str
    database: str
    created_at: datetime
    updated_at: datetime


class CreateProfileRequest(BaseModel):
    name: str
    host: str
    port: int = 3306
    user: str
    password: str
    database: str


class UpdateProfileRequest(BaseModel):
    name: str | None = None
    host: str | None = None
    port: int | None = None
    user: str | None = None
    password: str | None = None
    database: str | None = None


class AgentToggleState(BaseModel):
    analyze_slow_queries: bool = True
    analyze_running_queries: bool = True
    perform_incident_triage: bool = True
    check_replication_health: bool = True
    execute_database_query: bool = True
    get_skysql_observability_snapshot: bool = True


class AgentToggleResponse(BaseModel):
    toggles: AgentToggleState


class SessionMessage(BaseModel):
    role: str
    content: str
    created_at: datetime


class SessionData(BaseModel):
    id: str
    title: str
    messages: list[SessionMessage]
    created_at: datetime
    updated_at: datetime

