# Incident Triage Agent Test Scenarios

## Test Scenarios to Validate Agent Capabilities

### 1. Lock Contention Scenario
**Problem**: Long-running transaction blocking other queries
**What to create**:
- Start a transaction that holds locks for a long time
- Have other queries wait on those locks
- Agent should detect: `sys.innodb_lock_waits`, blocking queries

**Expected detection**:
- Lock wait patterns in sys schema
- Blocking query identification
- Wait duration analysis

### 2. Connection Exhaustion Scenario
**Problem**: Too many connections, approaching max_connections
**What to create**:
- Open many connections and keep them open
- Approach max_connections limit
- Agent should detect: High Threads_connected, connection errors

**Expected detection**:
- Threads_connected approaching max_connections
- Connection error patterns
- Connection pool issues

### 3. Long-Running Query Scenario
**Problem**: Queries running for a long time, consuming resources
**What to create**:
- Run queries that take 30+ seconds
- Multiple concurrent long-running queries
- Agent should detect: High execution time, resource usage

**Expected detection**:
- Long-running queries in processlist
- High CPU time or I/O time
- Resource consumption patterns

### 4. I/O Bottleneck Scenario
**Problem**: High disk I/O, slow queries due to disk access
**What to create**:
- Large table scans without indexes
- Multiple concurrent full table scans
- Agent should detect: High I/O latency, disk reads

**Expected detection**:
- High I/O latency in sys.io_global_by_file_by_latency
- Low buffer pool hit ratio
- Disk-bound queries

### 5. Memory Pressure Scenario
**Problem**: Temporary tables spilling to disk, memory pressure
**What to create**:
- Queries that create large temporary tables
- Queries that exceed tmp_table_size
- Agent should detect: Disk temp tables, memory pressure

**Expected detection**:
- High Created_tmp_disk_tables
- Memory pressure indicators
- Query performance degradation

### 6. Error Log Scenario
**Problem**: Errors in error log (already tested, but can combine)
**What to create**:
- Generate specific errors (connection errors, lock timeouts)
- Agent should detect: Error patterns, correlation with metrics

**Expected detection**:
- Error patterns in error log
- Correlation with current state
- Root cause identification

### 7. Mixed Incident Scenario
**Problem**: Multiple issues happening simultaneously
**What to create**:
- Lock contention + connection exhaustion
- Long-running queries + I/O bottlenecks
- Agent should detect: Multiple issues, prioritize correctly

**Expected detection**:
- Multiple patterns identified
- Correct prioritization
- Comprehensive analysis

## Test Program Design

### Features:
1. **Configurable scenarios**: Enable/disable specific problem types
2. **Controlled duration**: Problems run for specified time, then cleanup
3. **Safe cleanup**: All test connections/queries can be killed
4. **Monitoring**: Track what problems are active
5. **Error injection**: Generate specific errors for testing

### Safety Features:
- All test operations use test database/table
- Easy to identify test connections (specific user/comment)
- Automatic cleanup on exit
- Read-only operations where possible
- Timeout protection

## Implementation Plan

### Phase 1: Basic Scenarios
- Lock contention (simple blocking query)
- Long-running query (SLEEP or large scan)
- Connection exhaustion (open many connections)

### Phase 2: Advanced Scenarios
- I/O bottlenecks (large table scans)
- Memory pressure (large temp tables)
- Error injection (connection errors)

### Phase 3: Mixed Scenarios
- Multiple concurrent problems
- Problem escalation (one problem causes another)

## Test Database Setup

### Required:
- Test database: `test_incident_triage`
- Test table: `test_large_table` (with data)
- Test user: `test_incident_user` (with appropriate permissions)
- Performance Schema enabled (for sys schema tests)

### Optional:
- Large table for I/O tests (millions of rows)
- Indexed vs non-indexed tables for comparison


