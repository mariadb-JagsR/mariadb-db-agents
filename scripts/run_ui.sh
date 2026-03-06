#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Starting UI API backend on http://127.0.0.1:8000 ..."
python -m mariadb_db_agents.ui_api.main &
BACKEND_PID=$!

cleanup() {
  echo "Stopping backend..."
  kill "${BACKEND_PID}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "Starting React frontend on http://127.0.0.1:5173 ..."
cd "${ROOT_DIR}/ui_web"
npm install
npm run dev

