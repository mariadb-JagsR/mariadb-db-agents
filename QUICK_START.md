# Quick Start Guide

## Running Incident Triage Agent

### ✅ Recommended Method (Always Works)
```bash
cd /Users/jagsramnarayan-mariadb/Documents/skysql/develop/python_programs
source .venv/bin/activate
python -m mariadb_db_agents.cli.main incident-triage
```

### Alternative: Use the helper script
```bash
cd mariadb_db_agents
./RUN_INCIDENT_TRIAGE.sh
```

### With Error Log
```bash
python -m mariadb_db_agents.cli.main incident-triage \
    --error-log-path ~/Downloads/dbpgf05851876_jags-dont-delete-smalldb-mdb-ms-0_error-log_2025-12-16.log
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
cd /Users/jagsramnarayan-mariadb/Documents/skysql/develop/python_programs
source .venv/bin/activate
python -m mariadb_db_agents.cli.main incident-triage
```

## Database Configuration

Make sure your `.env` file has the correct database credentials:
```bash
DB_HOST=dbpgp29990659.sysp0000.db2.skysql.com
DB_PORT=3306
DB_USER=dbpgp29990659
DB_PASSWORD=aMWXUTkE3FYX!5rqCr3Lspghe
DB_DATABASE=mysql
```

SSL is automatically enabled for SkySQL hosts.

## All Available Agents

```bash
# Slow Query Agent
python -m mariadb_db_agents.cli.main slow-query --hours 1

# Running Query Agent
python -m mariadb_db_agents.cli.main running-query --min-time-seconds 5

# Incident Triage Agent
python -m mariadb_db_agents.cli.main incident-triage
```


