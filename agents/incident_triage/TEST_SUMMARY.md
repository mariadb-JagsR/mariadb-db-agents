# Incident Triage Agent Testing Summary

## What We've Created

### 1. Test Scenario Script
**File**: `scripts/create_incident_test_scenarios.py`

A comprehensive test program that creates real database problems to test the Incident Triage Agent.

**Features:**
- ✅ Lock contention (blocking queries)
- ✅ Connection exhaustion (too many connections)
- ✅ Long-running queries (resource consumption)
- ✅ I/O bottlenecks (disk I/O pressure)
- ✅ Safe cleanup (automatic connection/thread cleanup)
- ✅ Configurable duration
- ✅ Can run all scenarios simultaneously

### 2. Test Scenarios Documentation
**File**: `TEST_SCENARIOS.md`

Detailed documentation of:
- What each scenario creates
- What the agent should detect
- Expected outputs

### 3. Testing Guide
**File**: `TESTING_GUIDE.md`

Step-by-step guide for:
- Running each test scenario
- What to look for in agent output
- Manual testing methods
- Troubleshooting

## Quick Test Workflow

### Example: Test Lock Contention

**Step 1: Start the problem (Terminal 1)**
```bash
cd mariadb_db_agents
source ../.venv/bin/activate
python scripts/create_incident_test_scenarios.py --scenario lock_contention --duration 120
```

**Step 2: Run the agent (Terminal 2)**
```bash
cd mariadb_db_agents
source ../.venv/bin/activate
python -m cli.main incident-triage
```

**Step 3: Analyze results**
- Agent should detect lock contention
- Should identify blocking query
- Should provide recommendations

**Step 4: Cleanup (after test)**
```bash
python scripts/create_incident_test_scenarios.py --cleanup-only
```

## Test Scenarios Available

### 1. Lock Contention
**What it does:**
- Starts a long transaction that holds locks
- Has other queries wait on those locks
- Creates visible lock waits

**What agent should detect:**
- `sys.innodb_lock_waits` showing waiting queries
- Blocking query identification
- Wait duration

### 2. Connection Exhaustion
**What it does:**
- Opens many database connections
- Keeps them open
- Approaches max_connections limit

**What agent should detect:**
- High `Threads_connected`
- Connection errors (if max reached)
- Connection pool issues

### 3. Long-Running Queries
**What it does:**
- Runs queries that take 30+ seconds
- Multiple concurrent long queries
- Resource consumption

**What agent should detect:**
- High execution time in processlist
- High CPU or I/O time
- Resource consumption patterns

### 4. I/O Bottlenecks
**What it does:**
- Large table scans without indexes
- Multiple concurrent full scans
- High disk I/O

**What agent should detect:**
- High I/O latency in sys schema
- Low buffer pool hit ratio
- Disk-bound queries

## Safety Features

✅ **Test database isolation**: Uses test tables (`test_lock_table`, `test_large_table`)
✅ **Automatic cleanup**: All connections and threads cleaned up on exit
✅ **Timeout protection**: Scenarios run for specified duration then stop
✅ **Easy identification**: Test connections can be identified
✅ **Read-only where possible**: Most operations are safe

## Integration with Agent Features

### Performance Schema Integration
- Test scenarios work best when Performance Schema is enabled
- Agent will use sys schema tools automatically
- Falls back to SHOW STATUS if Performance Schema unavailable

### Error Log Integration
- Test scenarios can generate errors (connection errors, timeouts)
- Agent can analyze error logs alongside current state
- Provides complete picture of incident

## Next Steps

1. **Run basic test**: Start with lock contention scenario
2. **Verify detection**: Check that agent identifies the problem
3. **Test all scenarios**: Run each scenario individually
4. **Test combined**: Run all scenarios together (mixed incident)
5. **Test with error logs**: Point agent to error log during test
6. **Validate recommendations**: Check that agent suggestions are actionable

## Example Test Session

```bash
# 1. Start lock contention
python scripts/create_incident_test_scenarios.py --scenario lock_contention --duration 120 &
SCENARIO_PID=$!

# 2. Wait a few seconds for problem to establish
sleep 5

# 3. Run agent
python -m cli.main incident-triage

# 4. Review output - should show:
#    - Lock contention as top cause
#    - Blocking query details
#    - Recommendations

# 5. Cleanup
kill $SCENARIO_PID
python scripts/create_incident_test_scenarios.py --cleanup-only
```

## Validation Checklist

For each test scenario, verify:

- [ ] Agent detects the problem pattern
- [ ] Severity level is appropriate
- [ ] Key indicators are correct
- [ ] Immediate checks are actionable
- [ ] Safe mitigations are provided
- [ ] "What NOT to do" is clear
- [ ] Performance Schema data is used (if enabled)
- [ ] Error log analysis works (if error log provided)

## Troubleshooting

**Problem**: Test scenario doesn't create visible problems
- **Solution**: Check database permissions, verify max_connections setting

**Problem**: Agent doesn't detect the problem
- **Solution**: Check Performance Schema is enabled, verify database connection

**Problem**: Test tables already exist
- **Solution**: Run `--cleanup-only` first, then run scenario

**Problem**: Too many connections error
- **Solution**: Reduce number of connections in ConnectionExhaustionScenario


