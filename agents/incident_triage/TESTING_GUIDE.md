# Testing Guide for Incident Triage Agent

## Quick Start

### 1. Test Lock Contention
```bash
# Terminal 1: Create lock contention problem
cd mariadb_db_agents
source ../.venv/bin/activate
python scripts/create_incident_test_scenarios.py --scenario lock_contention --duration 120

# Terminal 2: Run Incident Triage Agent (while problem is active)
python -m cli.main incident-triage
```

### 2. Test Connection Exhaustion
```bash
# Terminal 1: Create connection exhaustion
python scripts/create_incident_test_scenarios.py --scenario connection_exhaustion --duration 60

# Terminal 2: Run agent
python -m cli.main incident-triage
```

### 3. Test Long-Running Queries
```bash
# Terminal 1: Create long-running queries
python scripts/create_incident_test_scenarios.py --scenario long_running --duration 90

# Terminal 2: Run agent
python -m cli.main incident-triage
```

### 4. Test I/O Bottlenecks
```bash
# Terminal 1: Create I/O intensive operations
python scripts/create_incident_test_scenarios.py --scenario io_intensive --duration 60

# Terminal 2: Run agent
python -m cli.main incident-triage
```

### 5. Test All Scenarios
```bash
# Terminal 1: Create all problems simultaneously
python scripts/create_incident_test_scenarios.py --scenario all --duration 120

# Terminal 2: Run agent
python -m cli.main incident-triage
```

## What to Look For

### Lock Contention Test
**Expected Detection:**
- ✅ `sys.innodb_lock_waits` should show waiting queries
- ✅ Blocking query identified
- ✅ Wait duration reported
- ✅ Locked table/index identified

**Agent should report:**
- "Lock Contention Pattern" as top cause
- Blocking query details
- Recommendations to kill blocking query or optimize

### Connection Exhaustion Test
**Expected Detection:**
- ✅ High `Threads_connected` approaching `max_connections`
- ✅ Connection errors (if max reached)
- ✅ Many idle connections

**Agent should report:**
- "Connection Exhaustion Pattern" as top cause
- Current connection count vs max
- Recommendations for connection pool tuning

### Long-Running Query Test
**Expected Detection:**
- ✅ Queries with high execution time in `sys.processlist`
- ✅ High CPU time or I/O time
- ✅ Queries in processlist with TIME > 30 seconds

**Agent should report:**
- "Query Performance Pattern" as top cause
- Long-running query details
- Recommendations to kill or optimize queries

### I/O Bottleneck Test
**Expected Detection:**
- ✅ High I/O latency in `sys.io_global_by_file_by_latency`
- ✅ Low buffer pool hit ratio
- ✅ High disk read operations

**Agent should report:**
- "Resource Pressure Pattern" as top cause
- I/O bottleneck tables/files
- Recommendations for indexing or buffer pool tuning

## Cleanup

After testing, clean up test tables:
```bash
python scripts/create_incident_test_scenarios.py --cleanup-only
```

## Manual Testing

You can also create problems manually:

### Lock Contention (Manual)
```sql
-- Terminal 1: Start blocking transaction
START TRANSACTION;
SELECT * FROM your_table WHERE id = 1 FOR UPDATE;
-- Keep this open

-- Terminal 2: Try to access same row
SELECT * FROM your_table WHERE id = 1 FOR UPDATE;
-- This will wait
```

### Connection Exhaustion (Manual)
```python
# Open many connections
import mysql.connector
connections = []
for i in range(100):
    conn = mysql.connector.connect(host=..., user=..., password=...)
    connections.append(conn)
    # Keep them open
```

## Testing with Error Logs

To test error log analysis:
1. Generate errors (connection errors, lock timeouts)
2. Point agent to error log:
```bash
python -m cli.main incident-triage --error-log-path /path/to/error.log
```

## Performance Schema Testing

To test sys schema integration:
1. Ensure Performance Schema is enabled
2. Run test scenarios
3. Agent should automatically use sys schema tools
4. Verify detailed metrics are reported

## Expected Agent Output

For each scenario, the agent should provide:

1. **Health Snapshot Summary**
   - Connection health status
   - Resource pressure indicators
   - Lock health status
   - Query activity metrics

2. **Top 3 Likely Causes**
   - Correct pattern identification
   - Severity and confidence levels
   - Key indicators with values

3. **Immediate Checks**
   - Specific SQL queries to run
   - Specific metrics to check
   - What to look for

4. **Safe Mitigations**
   - Actions that can be taken safely
   - Example: "Kill query ID X if safe"

5. **What NOT to Do**
   - Dangerous actions to avoid

## Troubleshooting

### Agent doesn't detect problems
- Check if Performance Schema is enabled
- Verify database connection is working
- Check if test scenario is actually creating problems
- Look at agent logs for errors

### Test scenario fails
- Check database permissions
- Verify max_connections setting (for connection exhaustion)
- Check if test tables exist
- Review error messages

### Agent reports false positives
- This is expected - agent may identify patterns that aren't critical
- Focus on severity and confidence levels
- Review "Key Indicators" to understand why agent flagged it


