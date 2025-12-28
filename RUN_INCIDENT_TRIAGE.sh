#!/bin/bash
# Quick script to run Incident Triage Agent
# This avoids the package import issues

cd "$(dirname "$0")/.."
source .venv/bin/activate

# Run using module syntax (most reliable)
python -m mariadb_db_agents.cli.main incident-triage "$@"


