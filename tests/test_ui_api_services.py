from __future__ import annotations

import json
from pathlib import Path

from mariadb_db_agents.ui_api import config_service
from mariadb_db_agents.ui_api import orchestrator_service
from mariadb_db_agents.ui_api.next_steps import extract_next_steps
from mariadb_db_agents.ui_api.schemas import AgentToggleState, CreateProfileRequest


def test_extract_next_steps_from_markdown() -> None:
    payload = """
## Recommendations
- Run SHOW PROCESSLIST and identify blocking sessions
2. Add an index on orders(created_at)
## Notes
No other findings.
"""
    steps = extract_next_steps(payload)
    assert steps == [
        "Run SHOW PROCESSLIST and identify blocking sessions",
        "Add an index on orders(created_at)",
    ]


def test_extract_next_steps_with_bold_heading() -> None:
    payload = """
**Next Steps:**
1. Review lock wait graph for top blockers
- Run `SHOW ENGINE INNODB STATUS`

### Follow-up
Anything else.
"""
    steps = extract_next_steps(payload)
    assert steps == [
        "Review lock wait graph for top blockers",
        "Run SHOW ENGINE INNODB STATUS",
    ]


def test_profile_activation_updates_env(monkeypatch, tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    profiles_path = tmp_path / "profiles.json"
    sessions_path = tmp_path / "sessions.json"
    toggles_path = tmp_path / "toggles.json"
    ui_data = tmp_path

    monkeypatch.setattr(config_service, "ENV_PATH", env_path)
    monkeypatch.setattr(config_service, "PROFILES_PATH", profiles_path)
    monkeypatch.setattr(config_service, "SESSIONS_PATH", sessions_path)
    monkeypatch.setattr(config_service, "TOGGLES_PATH", toggles_path)
    monkeypatch.setattr(config_service, "UI_DATA_DIR", ui_data)

    profile = config_service.create_profile(
        CreateProfileRequest(
            name="local",
            host="127.0.0.1",
            port=3307,
            user="readonly",
            password="secret",
            database="analytics",
        )
    )
    config_service.activate_profile(profile.id)

    env_text = env_path.read_text(encoding="utf-8")
    assert "DB_HOST=127.0.0.1" in env_text
    assert "DB_PORT=3307" in env_text
    assert "DB_USER=readonly" in env_text
    assert "DB_PASSWORD=secret" in env_text
    assert "DB_DATABASE=analytics" in env_text

    env_values = config_service.get_env_values(redact_secrets=True)
    assert env_values["DB_PASSWORD"] == config_service.SECRET_MASK

    redacted = config_service.list_profiles_redacted()
    assert redacted["profiles"][0]["password"] == config_service.SECRET_MASK


def test_toggle_persistence(monkeypatch, tmp_path: Path) -> None:
    toggles_path = tmp_path / "toggles.json"
    monkeypatch.setattr(config_service, "TOGGLES_PATH", toggles_path)

    toggles = AgentToggleState(analyze_slow_queries=False)
    saved = config_service.set_agent_toggles(toggles)
    loaded = config_service.get_agent_toggles()
    assert saved.analyze_slow_queries is False
    assert loaded.analyze_slow_queries is False

    raw = json.loads(toggles_path.read_text(encoding="utf-8"))
    assert raw["toggles"]["analyze_slow_queries"] is False


def test_history_is_included_in_effective_prompt(monkeypatch) -> None:
    monkeypatch.setattr(
        orchestrator_service,
        "get_session_by_id",
        lambda _session_id: {
            "id": "s1",
            "messages": [
                {"role": "user", "content": "How is DB health?"},
                {"role": "assistant", "content": "Health looks stable."},
            ],
        },
    )
    prompt = orchestrator_service._build_prompt_with_history("s1", "Any slow queries now?")
    assert "USER: How is DB health?" in prompt
    assert "ASSISTANT: Health looks stable." in prompt
    assert "USER (current question):" in prompt
    assert "Any slow queries now?" in prompt


def test_long_history_adds_summary_and_recent_turns(monkeypatch) -> None:
    messages = []
    for i in range(18):
        role = "user" if i % 2 == 0 else "assistant"
        messages.append({"role": role, "content": f"message {i} " + ("x" * 220)})

    monkeypatch.setattr(
        orchestrator_service,
        "get_session_by_id",
        lambda _session_id: {"id": "s2", "messages": messages},
    )

    prompt = orchestrator_service._build_prompt_with_history("s2", "final question")
    assert "Earlier context summary:" in prompt
    assert "USER (current question):" in prompt
    assert "final question" in prompt
    # Recent messages still appear explicitly.
    assert "message 17" in prompt

