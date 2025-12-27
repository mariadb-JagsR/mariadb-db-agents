# Quick Test Guide for Incident Triage Agent

## Correct Way to Run

### Option 1: Using the CLI module (Recommended)
```bash
cd mariadb_db_agents
source ../.venv/bin/activate
python -m cli.main incident-triage
```

### Option 2: Using the full module path
```bash
cd /Users/jagsramnarayan-mariadb/Documents/skysql/develop/python_programs
source .venv/bin/activate
python -m mariadb_db_agents.cli.main incident-triage
```

### Option 3: Direct agent execution
```bash
cd mariadb_db_agents
source ../.venv/bin/activate
python -m agents.incident_triage.main
```

## Testing with Error Log

```bash
python -m cli.main incident-triage --error-log-path ~/Downloads/dbpgf05851876_jags-dont-delete-smalldb-mdb-ms-0_error-log_2025-12-16.log
```

## Testing with Problem Scenarios

### Step 1: Create a problem (Terminal 1)
```bash
cd mariadb_db_agents
source ../.venv/bin/activate
python scripts/create_incident_test_scenarios.py --scenario lock_contention --duration 120
```

### Step 2: Run agent (Terminal 2)
```bash
cd mariadb_db_agents
source ../.venv/bin/activate
python -m cli.main incident-triage
```

## Troubleshooting Import Errors

If you get "ImportError: attempted relative import beyond top-level package":

1. **Make sure you're in the right directory:**
   ```bash
   cd mariadb_db_agents
   ```

2. **Make sure virtual environment is activated:**
   ```bash
   source ../.venv/bin/activate
   ```

3. **Use the module syntax:**
   ```bash
   python -m cli.main incident-triage
   ```
   NOT: `python cli/main.py incident-triage`

4. **If still having issues, use full path:**
   ```bash
   cd /Users/jagsramnarayan-mariadb/Documents/skysql/develop/python_programs
   source .venv/bin/activate
   python -m mariadb_db_agents.cli.main incident-triage
   ```


