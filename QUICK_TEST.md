# Quick Testing Guide

## Prerequisites Check

1. **Activate the virtual environment:**
   ```bash
   source ../.venv/bin/activate
   ```

2. **Create .env file** (if not already created):
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   ```

## Testing Steps

### Step 1: Generate Slow Queries (Optional - if you need test data)

```bash
# Make sure you're in mariadb_db_agents directory
cd mariadb_db_agents

# Activate venv
source ../.venv/bin/activate

# Generate slow queries (runs each query 2 times)
python scripts/generate_slow_queries_reviewed.py 2
```

This will create entries in `mysql.slow_log` that the agent can analyze.

### Step 2: Test Slow Query Agent

**Option A: Using Unified CLI (Recommended)**
```bash
python -m mariadb_db_agents.cli.main slow-query \
  --hours 1 \
  --max-patterns 5
```

**Option B: Direct Agent Entry Point**
```bash
python -m mariadb_db_agents.agents.slow_query.main \
  --hours 1 \
  --max-patterns 5
```

**Option C: Interactive Mode**
```bash
python -m mariadb_db_agents.cli.main slow-query --interactive
```

### Step 3: Test Running Query Agent

**In one terminal - Start a long-running query:**
```sql
-- Connect to your database and run:
SELECT * FROM beer_reviews.beer_reviews_flat 
WHERE review_text LIKE '%test%' 
ORDER BY review_time DESC;
```

**In another terminal - Run the agent:**
```bash
# Activate venv
source ../.venv/bin/activate

# Run the agent
python -m mariadb_db_agents.cli.main running-query \
  --min-time-seconds 1.0
```

**Or in interactive mode:**
```bash
python -m mariadb_db_agents.cli.main running-query --interactive
```

## Example Commands

**Example for slow query agent:**
```bash
python -m mariadb_db_agents.cli.main slow-query \
  --hours 1 \
  --max-patterns 5
```

**Example for running query agent:**
```bash
python -m mariadb_db_agents.cli.main running-query \
  --min-time-seconds 1.0
```

**Note**: Database connection is configured via environment variables (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_DATABASE) in the `.env` file.

## Troubleshooting

**If you get "No slow queries found":**
- Make sure slow query logging is enabled on your database
- Try increasing `--hours` (e.g., `--hours 24`)
- Check that queries were actually slow (>5 seconds)

**If you get import errors:**
- Make sure you activated the venv: `source ../.venv/bin/activate`
- Make sure you're in the `mariadb_db_agents` directory

**If you get database connection errors:**
- Check your `.env` file has correct credentials
- Verify database is accessible

## What to Expect

**Slow Query Agent Output:**
- Summary of slow query patterns found
- For each pattern: query analysis, execution plan, index recommendations
- Performance metrics (if Performance Schema enabled)
- Optimization suggestions

**Running Query Agent Output:**
- List of currently running queries
- Problem identification (long-running, blocking, etc.)
- Recommendations for each problematic query

