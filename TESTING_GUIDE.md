# Testing Guide

This guide will help you test the MariaDB Database Management Agents.

## Prerequisites

1. **Database Setup**: You need a MariaDB/MySQL database with:
   - A table with sufficient data (e.g., `beer_reviews.beer_reviews_flat` with ~2.9M rows)
   - Slow query logging enabled (see optional setup below)
   - Performance Schema enabled (optional but recommended)

2. **Environment Configuration**: 
   - Copy `.env.example` to `.env` and fill in your database credentials
   - Set `OPENAI_API_KEY` in your `.env` file

## Step 1: Generate Slow Queries

Performance Schema provides detailed metrics (CPU time, lock wait time, I/O stats):

```bash
# Run the SQL script
mysql -h <host> -u <user> -p < mariadb_db_agents/enable_performance_schema.sql
```

Or manually:
```sql
SET GLOBAL performance_schema = ON;
-- Then run the commands in enable_performance_schema.sql
```

## Step 3: Generate Slow Queries

Run the script to generate slow queries in your database:

### Option A: Use the Reviewed Version (Safer)

```bash
cd mariadb_db_agents
python scripts/generate_slow_queries_reviewed.py [num_iterations]
```

**Example:**
```bash
python scripts/generate_slow_queries_reviewed.py 2
```

This will run each slow query 2 times. The reviewed version excludes dangerous queries that could hang.

### Option B: Use the Full Version (More Queries, Some May Be Slow)

```bash
python scripts/generate_slow_queries.py [num_iterations]
```

**Example:**
```bash
python scripts/generate_slow_queries.py 3
```

### What the Scripts Do

The scripts run complex queries designed to take >5 seconds:
- Full table scans with text search (LIKE on TEXT columns)
- Complex aggregations with GROUP BY
- Window functions with partitioning
- Subqueries
- Multiple LIKE conditions on TEXT columns

These queries will generate entries in `mysql.slow_log` that the agent can analyze.

## Step 2: Test the Slow Query Agent

Once you have slow queries in the log, test the agent:

### Using Unified CLI (Recommended)

```bash
python -m mariadb_db_agents.cli.main slow-query \
  --hours 1 \
  --max-patterns 5
```

**Example:**
```bash
python -m mariadb_db_agents.cli.main slow-query \
  --hours 1 \
  --max-patterns 5
```

### Using Direct Agent Entry Point

```bash
python -m mariadb_db_agents.agents.slow_query.main \
  --hours 1 \
  --max-patterns 5
```

### Interactive Mode

For a conversation-based interaction:

```bash
python -m mariadb_db_agents.cli.main slow-query --interactive
```

Or directly:
```bash
python -m mariadb_db_agents.agents.slow_query.conversation
```

**Note**: Database connection is configured via environment variables (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_DATABASE) in the `.env` file.

## Step 3: Test the Running Query Agent

The running query agent analyzes currently executing queries. To test it:

1. **Start a long-running query** in another terminal:
   ```sql
   -- In MySQL client
   SELECT * FROM beer_reviews.beer_reviews_flat 
   WHERE review_text LIKE '%test%' 
   ORDER BY review_time DESC;
   ```

2. **Run the running query agent** (in another terminal):
   ```bash
   python -m mariadb_db_agents.cli.main running-query \
     --min-time-seconds 1.0
   ```

   Or in interactive mode:
   ```bash
   python -m mariadb_db_agents.cli.main running-query --interactive
   ```

## Optional Setup

### Enable Slow Query Logging (If Not Already Enabled)

If slow query logging is not enabled on your database, you can enable it:

```sql
-- Check current status
SHOW VARIABLES LIKE 'slow_query_log';
SHOW VARIABLES LIKE 'long_query_time';
SHOW VARIABLES LIKE 'log_output';

-- Enable slow query logging (if not already enabled)
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 5.0;  -- Log queries taking >= 5 seconds
SET GLOBAL log_output = 'TABLE';   -- Store in mysql.slow_log table (recommended)

-- Verify
SHOW VARIABLES LIKE 'slow_query_log';
```

**Note**: If `log_output` is set to `FILE`, the agent will need access to the log file path. `TABLE` is recommended for easier access.

### Enable Performance Schema (Optional but Recommended)

Performance Schema provides detailed metrics (CPU time, lock wait time, I/O stats):

```bash
# Run the SQL script
mysql -h <host> -u <user> -p < mariadb_db_agents/enable_performance_schema.sql
```

Or manually:
```sql
SET GLOBAL performance_schema = ON;
-- Then run the commands in enable_performance_schema.sql
```

## Troubleshooting

### No Slow Queries Found

If the agent reports no slow queries:
1. **Check slow query log is enabled**: `SHOW VARIABLES LIKE 'slow_query_log';` (see Optional Setup above)
2. **Check time window**: Try increasing `--hours` (e.g., `--hours 24`)
3. **Check long_query_time**: If it's too high, queries might not be logged:
   ```sql
   SHOW VARIABLES LIKE 'long_query_time';
   -- Lower it if needed: SET GLOBAL long_query_time = 1.0;
   ```
4. **Verify queries were actually slow**: Check `mysql.slow_log`:
   ```sql
   SELECT COUNT(*) FROM mysql.slow_log 
   WHERE start_time >= DATE_SUB(NOW(), INTERVAL 1 HOUR);
   ```

### Performance Schema Not Available

If you see "Performance Schema is not enabled":
- The agent will still work, but with limited metrics
- To enable: Run `enable_performance_schema.sql` or set `performance_schema = ON` in your config

### Import Errors

If you get import errors:
1. Make sure you're in the correct directory
2. Ensure the virtual environment is activated
3. Check that all dependencies are installed: `pip install -r requirements.txt`

### Database Connection Issues

If connection fails:
1. Check `.env` file has correct credentials
2. Verify database is accessible from your machine
3. Check firewall/network settings
4. For SkySQL: Ensure IP allowlist includes your IP

## Expected Output

### Slow Query Agent Output

The agent should provide:
- Summary of slow query patterns found
- For each pattern:
  - Query structure and metrics
  - Execution plan analysis
  - Index analysis
  - Performance metrics (if Performance Schema enabled)
  - Recommendations (query rewrites, indexes, configuration)

### Running Query Agent Output

The agent should provide:
- List of currently running queries
- Problem identification (long-running, blocking, etc.)
- For each problematic query:
  - Execution plan
  - Performance metrics
  - Recommendations (kill query, optimize, etc.)

## Next Steps

After testing:
1. Review the agent recommendations
2. Try implementing suggested optimizations
3. Re-run the agent to see improvements
4. Explore interactive mode for deeper analysis

For more information, see the main [README.md](README.md).

