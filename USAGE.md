# Quick Usage Guide

## Running from Any Directory

### Option 1: Use the wrapper script (Easiest)

```bash
# From anywhere, activate venv first
source /Users/jagsramnarayan-mariadb/Documents/skysql/develop/python_programs/.venv/bin/activate

# Then run the wrapper script
python mariadb_db_agents/mariadb-db-agents slow-query --hours 1
python mariadb_db_agents/mariadb-db-agents running-query --min-time-seconds 1.0
```

### Option 2: Run from parent directory (python_programs)

```bash
cd /Users/jagsramnarayan-mariadb/Documents/skysql/develop/python_programs
source .venv/bin/activate
python -m mariadb_db_agents.cli.main slow-query --hours 1
python -m mariadb_db_agents.cli.main running-query --min-time-seconds 1.0
```

### Option 3: Set PYTHONPATH

```bash
export PYTHONPATH=/Users/jagsramnarayan-mariadb/Documents/skysql/develop/python_programs:$PYTHONPATH
source .venv/bin/activate
python -m mariadb_db_agents.cli.main slow-query --hours 1
```

## Common Commands

**Slow Query Agent:**
```bash
# One-time analysis
python -m mariadb_db_agents.cli.main slow-query --hours 1 --max-patterns 5

# Interactive mode
python -m mariadb_db_agents.cli.main slow-query --interactive
```

**Running Query Agent:**
```bash
# One-time analysis
python -m mariadb_db_agents.cli.main running-query --min-time-seconds 1.0

# Interactive mode
python -m mariadb_db_agents.cli.main running-query --interactive
```

## Environment Setup

Make sure your `.env` file in `mariadb_db_agents/` contains:
```
OPENAI_API_KEY=your-key
OPENAI_MODEL=gpt-4o-mini
DB_HOST=your-host
DB_PORT=3306
DB_USER=your-user
DB_PASSWORD=your-password
DB_DATABASE=your-database
```

