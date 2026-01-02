# Incident Triage Agent

## Overview

The Incident Triage Agent is designed to quickly identify what's wrong with a database and provide a prioritized checklist of where to look first. It's the "something's wrong, where do I start?" agent.

## Features

- **Health Snapshot**: Gathers a minimal "golden snapshot" of critical health metrics
- **Performance Schema Integration**: Uses `performance_schema` and `information_schema` tables directly for real-time metrics (when available)
- **SkySQL Observability**: Fetches CPU% and disk utilization metrics from SkySQL Observability API (not accessible via SQL)
- **Symptom Correlation**: Identifies top 2-3 likely causes based on health metrics
- **Error Log Analysis**: Reads and analyzes error logs with intelligent pattern extraction (supports local files and SkySQL API)
- **Prioritized Checklist**: Provides immediate checks, safe mitigations, and what NOT to do
- **Conservative Reporting**: Only reports actual problems, not normal operations

### Performance Schema Tools

When Performance Schema is enabled, the agent directly queries `performance_schema` and `information_schema` tables:

- **performance_schema.events_statements_summary_by_digest**: Aggregated statement statistics
- **information_schema.innodb_lock_waits**: Current lock contention with blocking queries
- **information_schema.processlist**: Enhanced process list with query details
- **performance_schema.metadata_locks**: Table-level lock waits (metadata locks)
- **performance_schema.file_io_summary_by_file**: I/O bottlenecks by table/file
- **performance_schema.events_statements_summary_by_digest**: Most resource-intensive statements

If Performance Schema is not enabled, the agent gracefully falls back to SHOW STATUS and information_schema queries.

**Note**: The agent uses `performance_schema` and `information_schema` directly, not `sys` schema views, for broader compatibility.

## Error Log Access

The agent supports two methods for accessing error logs:

1. **Local File Access** (for development/testing):
   ```bash
   mariadb-db-agents incident-triage --error-log-path /var/log/mysql/error.log
   ```
   **Priority**: If `--error-log-path` is provided, the agent reads only from that file (not from SkySQL API).

2. **SkySQL API** (for production):
   ```bash
   mariadb-db-agents incident-triage
   ```
   Automatically uses SkySQL API if `SKYSQL_API_KEY` and `SKYSQL_SERVICE_ID` are set in environment.

### Error Log Pattern Extraction

The error log tool (`read_error_log`) intelligently extracts patterns from error logs to avoid sending huge files to the LLM:

- **Normalizes error messages**: Replaces timestamps, PIDs, connection IDs, database/table names
- **Groups similar errors**: Counts occurrences of each pattern
- **Severity classification**: Categorizes errors as ERROR, WARNING, or INFO
- **Time tracking**: Records first_seen and last_seen timestamps
- **Sample messages**: Provides one example of each error pattern

This preprocessing dramatically reduces the amount of data sent to the LLM while preserving the essential information needed for diagnosis.

## Usage

### CLI Mode

```bash
# Basic usage (will attempt to read error log if path/service_id provided)
python -m mariadb_db_agents.cli.main incident-triage

# With local error log file
python -m mariadb_db_agents.cli.main incident-triage --error-log-path /var/log/mysql/error.log

# With SkySQL service ID (requires API implementation)
python -m mariadb_db_agents.cli.main incident-triage --service-id <service_id>

# Customize error log analysis
python -m mariadb_db_agents.cli.main incident-triage \
    --error-log-path /var/log/mysql/error.log \
    --max-error-patterns 30 \
    --error-log-lines 10000
```

### Direct Agent Access

```bash
python -m mariadb_db_agents.agents.incident_triage.main \
    --error-log-path /var/log/mysql/error.log
```

## Health Metrics Collected

The agent gathers a minimal set of critical health indicators:

### Connection Health
- Threads_connected, Max_used_connections, max_connections
- Threads_running
- Connection errors (Aborted_connects, Connection_errors_%)

### Resource Pressure
- Thread creation rate
- Temporary table usage (memory vs disk)
- Table lock waits
- Buffer pool statistics (hit ratio, I/O)
- **CPU usage** (SkySQL only, via Observability API)
- **Disk utilization** (SkySQL only, via Observability API - data and logs volumes)

### Lock & Transaction Health
- InnoDB lock waits
- Current lock information
- Average lock wait time

### Replication Health (if applicable)
- Replication lag
- IO/SQL thread status
- Replication errors

### Query Activity
- Query rates (Questions, Slow_queries)
- Command statistics (SELECT, INSERT, UPDATE, DELETE)
- Long-running queries

### Error Log Analysis
- Error patterns (grouped and counted)
- Severity classification
- Time-based analysis

## Output Format

The agent provides:

1. **Health Snapshot Summary**: Quick status of all health areas
2. **Top 3 Likely Causes**: Ranked by severity and confidence
   - Pattern name and severity
   - Key indicators (metrics)
   - 5 immediate checks
   - 2-3 safe mitigations
   - What NOT to do
3. **Error Log Analysis**: Summary of error patterns and correlations
4. **Next Steps**: Prioritized action items

## Implementation Notes

### Error Log Tool Implementation

The `tail_error_log_file` function in `common/db_client.py`:

- **Local file access**: Implemented - reads from filesystem
- **SkySQL API**: Fully implemented - fetches error logs from SkySQL Observability API
- **Priority**: Explicit file paths take precedence over SkySQL API

### SkySQL Observability Integration

The agent can fetch CPU% and disk utilization metrics via `get_skysql_observability_snapshot()`:

- **Automatic region detection**: Fetches deployment region from SkySQL Provisioning API
- **Metrics provided**: CPU usage, disk volume utilization (data/logs), threads, aborted connections
- **Threshold warnings**: Automatically flags high CPU (>85%) and disk usage (>90%)
- **Integration**: Used in resource pressure analysis when available

### Pattern Extraction Algorithm

The pattern extraction:
1. Normalizes error messages (removes timestamps, PIDs, etc.)
2. Groups similar errors together
3. Counts occurrences
4. Classifies severity
5. Tracks time ranges
6. Returns top N patterns (default: 20)

This preprocessing ensures the LLM receives structured, actionable data rather than raw log dumps.

## Integration with Other Agents

The Incident Triage Agent can act as a **meta-agent** that coordinates with other agents:

- **Slow Query Agent**: For deeper analysis of slow query patterns
- **Running Query Agent**: For real-time query analysis
- **Future agents**: Replication Health, Lock Detective, etc.

The agent suggests using other agents when deeper analysis is needed.

## Example Output

```
## Health Snapshot Summary
- Connection health: CRITICAL (Threads_connected: 3498/3500)
- Resource pressure: HIGH (Buffer pool hit ratio: 0.65)
- Lock health: MEDIUM (Current lock waits: 3)
- Error log status: 15 error patterns found, 3 CRITICAL

## Top 3 Likely Causes

### Cause 1: Connection Exhaustion
**Severity:** CRITICAL
**Confidence:** HIGH
**Key Indicators:**
- Threads_connected: 3498 (normal range: 0-1000)
- Max_used_connections: 3500
- Connection_errors_max_connections: 127

**5 Immediate Checks:**
1. Check processlist for idle connections: SELECT * FROM information_schema.processlist WHERE COMMAND='Sleep'
2. Review connection pool configuration in applications
3. Check for connection leaks (long-lived idle connections)
4. Review max_connections setting: SHOW VARIABLES LIKE 'max_connections'
5. Check error log for connection-related errors

**2-3 Safe Mitigations:**
1. Identify and kill idle connections if safe (check what they're doing first)
2. Review application connection pool settings
3. Consider increasing max_connections if justified by workload

**What NOT to Do:**
- Do NOT increase max_connections without understanding why connections aren't being released
- Do NOT kill connections without checking for active transactions
```

## Future Enhancements

- Historical trend analysis (compare current state to baseline)
- Automated alerting based on health snapshot thresholds
- Integration with monitoring systems (Prometheus, Grafana)
- Agent composition (automatically call other agents for deeper analysis)
- Historical observability metrics (currently snapshot-only)

