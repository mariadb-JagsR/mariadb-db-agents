# Performance Schema (sys schema) Integration for Incident Triage

## Why Performance Schema in Incident Triage Agent?

**Answer: It should be part of the Incident Triage Agent, not a separate agent.**

### Rationale:

1. **Real-time incident analysis requires real-time metrics**
   - Performance Schema provides current state, not historical
   - Perfect for "something's wrong right now" scenarios
   - Complements error log analysis (which is historical)

2. **Sys schema provides human-readable views**
   - `sys.metrics` - system-wide health metrics
   - `sys.innodb_lock_waits` - current lock contention
   - `sys.processlist` - enhanced process list with performance data
   - `sys.statement_analysis` - resource-intensive queries
   - `sys.io_global_by_file_by_latency` - I/O bottlenecks

3. **Incident triage needs multiple data sources**
   - Error logs (what went wrong)
   - Performance Schema (what's happening now)
   - SHOW STATUS (basic metrics)
   - All should be in one agent for correlation

4. **Graceful degradation**
   - If Performance Schema not enabled, falls back to SHOW STATUS
   - Agent still works, just with less detail

## Sys Schema Tools Added

### 1. `get_sys_metrics()`
**Purpose**: System-wide health metrics
**Use case**: Quick overview of database health
**Returns**: Connection metrics, query rates, InnoDB metrics, lock metrics, I/O metrics

### 2. `get_sys_innodb_lock_waits()`
**Purpose**: Current InnoDB lock contention
**Use case**: Identify blocking queries and lock waits
**Returns**: Which transactions are waiting, which are blocking, wait duration

### 3. `get_sys_processlist()`
**Purpose**: Enhanced process list with Performance Schema metrics
**Use case**: Better than information_schema.processlist - includes CPU time, lock latency
**Returns**: Processes with statement latency, CPU time, lock wait time

### 4. `get_sys_schema_table_lock_waits()`
**Purpose**: Table-level lock waits (metadata locks)
**Use case**: DDL operations blocking queries
**Returns**: Which queries are waiting for table locks, blocking queries

### 5. `get_sys_io_global_by_file_by_latency()`
**Purpose**: I/O bottlenecks by file/table
**Use case**: Identify which tables are causing disk I/O issues
**Returns**: Files with highest I/O latency, read/write statistics

### 6. `get_sys_statement_analysis()`
**Purpose**: Most resource-intensive statements
**Use case**: Identify problematic queries during incidents
**Returns**: Queries with highest latency, CPU time, lock waits

## Integration Strategy

### Priority Order:
1. **Try sys schema tools first** (if Performance Schema enabled)
2. **Fall back to SHOW STATUS** (if sys schema unavailable)
3. **Use information_schema** (for basic processlist, locks)

### Example Workflow:

```
Incident Triage Agent:
1. Check if Performance Schema enabled
2. If yes:
   - get_sys_metrics() → system health overview
   - get_sys_innodb_lock_waits() → lock contention
   - get_sys_processlist() → current queries
   - get_sys_statement_analysis() → problematic queries
   - get_sys_io_global_by_file_by_latency() → I/O bottlenecks
3. If no:
   - SHOW STATUS queries
   - information_schema.processlist
   - information_schema.innodb_locks
4. read_error_log() → error patterns
5. Correlate all data sources
6. Generate triage report
```

## Benefits Over Separate Agent

### If Performance Schema was a separate agent:
- ❌ Would require running two agents for complete analysis
- ❌ Harder to correlate Performance Schema data with error logs
- ❌ More complex for users ("run incident triage, then run perf schema agent")
- ❌ Duplicate health snapshot gathering

### With Performance Schema integrated:
- ✅ Single agent provides complete incident analysis
- ✅ Automatic correlation of all data sources
- ✅ Graceful degradation if Performance Schema unavailable
- ✅ Better user experience (one command, complete analysis)

## Comparison: sys schema vs SHOW STATUS

| Aspect | sys schema | SHOW STATUS |
|--------|-----------|-------------|
| **Real-time** | ✅ Current state | ⚠️ Aggregated since startup |
| **Lock details** | ✅ Blocking queries, wait times | ❌ Only counts |
| **Query details** | ✅ CPU time, lock latency per query | ❌ Only aggregates |
| **I/O details** | ✅ Per-file/table latency | ❌ Only totals |
| **Availability** | ⚠️ Requires Performance Schema | ✅ Always available |
| **Overhead** | ⚠️ Some overhead | ✅ Minimal overhead |

## When to Use Each

### Use sys schema when:
- ✅ Performance Schema is enabled
- ✅ Need detailed lock wait information
- ✅ Need per-query performance metrics
- ✅ Need I/O bottleneck identification
- ✅ Incident is happening NOW (real-time analysis)

### Use SHOW STATUS when:
- ✅ Performance Schema not enabled
- ✅ Need basic aggregated metrics
- ✅ Historical trends (since server startup)
- ✅ Minimal overhead required

## Example: Lock Contention Incident

### With sys schema:
```python
lock_waits = get_sys_innodb_lock_waits()
# Returns:
# - waiting_query: "SELECT * FROM orders WHERE user_id = 123"
# - blocking_query: "UPDATE orders SET status = 'shipped' WHERE id = 456"
# - wait_age_secs: 45.2
# - locked_table: "orders"
# - locked_index: "PRIMARY"
```

**Analysis**: "Query on orders table blocked by UPDATE for 45 seconds"

### Without sys schema (fallback):
```sql
SHOW STATUS LIKE 'Innodb_row_lock_current_waits'
-- Returns: 3
SHOW ENGINE INNODB STATUS
-- Parse text output for lock info
```

**Analysis**: "3 lock waits detected, need to parse InnoDB status for details"

## Conclusion

**Performance Schema integration belongs in the Incident Triage Agent** because:

1. ✅ Provides real-time data needed for incident analysis
2. ✅ Complements error log analysis (historical + current)
3. ✅ Single agent provides complete picture
4. ✅ Graceful degradation if unavailable
5. ✅ Better user experience (one command)

The sys schema tools are now integrated and will be used automatically when Performance Schema is enabled, with automatic fallback to SHOW STATUS when it's not.

