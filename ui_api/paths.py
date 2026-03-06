from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
UI_DATA_DIR = PROJECT_ROOT / ".ui_data"
ENV_PATH = PROJECT_ROOT / ".env"

PROFILES_PATH = UI_DATA_DIR / "profiles.json"
TOGGLES_PATH = UI_DATA_DIR / "agent_toggles.json"
SESSIONS_PATH = UI_DATA_DIR / "sessions.json"
RUN_HISTORY_PATH = UI_DATA_DIR / "run_history.json"
