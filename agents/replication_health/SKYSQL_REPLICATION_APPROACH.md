# Replication Health Agent - SkySQL/MaxScale Approach

## Problem Statement

In SkySQL (MariaDB Cloud), MaxScale is used as a load balancer in front of the database servers. When we connect to the database, we're connecting through MaxScale, not directly to individual servers. This means:

1. **We can't directly query individual replicas** - all queries go through MaxScale
2. **We don't know which server we're connected to** - MaxScale load balances requests
3. **We need a way to discover all replicas** in the service
4. **We need to get replication status from each replica** individually

## Existing Solution (from copilot/lib/database.py)

The existing codebase has a workaround in `fetch_replica_status()`:

```python
def fetch_replica_status(host, username, password, port, database):
    """Workaround to fetch replica status.
    We fetch a connection, turn on autocommit and execute the SQL multiple times.
    This will result in maxscale round-robin algo to execute on a Slave.
    """
    engine = raw_engine(username, password, host, port, database)
    
    with engine.connect() as connection:
        connection.execute(text("SET autocommit = 1"))
        sql_query = text("SHOW ALL SLAVES STATUS")
        combined_results = []
        
        # Execute 6 times - MaxScale round-robin will hit different slaves
        for _ in range(6):
            results = connection.execute(sql_query)
            # ... collect results ...
        
        return combined_results
```

### How It Works

1. **Enable autocommit**: `SET autocommit = 1` - This makes each query a separate transaction
2. **Execute multiple times**: Run `SHOW ALL SLAVES STATUS` 6 times
3. **MaxScale round-robin**: Each execution gets load-balanced to a different server
4. **Collect results**: Combine results from all replicas
5. **Skip primary**: When query hits primary, it returns no results (skipped)

### Limitations

- **Not deterministic**: Can't guarantee which replica you hit
- **May hit same replica multiple times**: Round-robin might not be perfect
- **May miss replicas**: If there are more than 6 replicas, some might be missed
- **No direct server identification**: Can't tell which server each result came from
- **MaxScale hinting doesn't work**: Comment says "get maxscale hinting to work correctly. In my testing from Python it doesn't."

## Proposed Approach for Replication Health Agent

### Option 1: Use Existing Workaround (Recommended for Phase 1)

**Approach**: Use the same `SHOW ALL SLAVES STATUS` with multiple executions

**Advantages**:
- ✅ Already proven to work
- ✅ Simple to implement
- ✅ Works with current MaxScale setup
- ✅ No API dependencies

**Disadvantages**:
- ⚠️ Not deterministic (might miss replicas)
- ⚠️ Can't identify which server each result is from
- ⚠️ May need to execute more times if many replicas

**Implementation**:
```python
@function_tool
def get_all_replica_status(
    max_executions: int = 10,
) -> dict[str, Any]:
    """
    Get replication status from all replicas in a SkySQL service.
    
    Uses MaxScale round-robin load balancing by executing SHOW ALL SLAVES STATUS
    multiple times. Each execution may hit a different replica.
    
    Args:
        max_executions: Number of times to execute the query (default: 10)
                       Increase if you have many replicas
    
    Returns:
        Dictionary with 'replicas' list containing status from each replica found
    """
    # Execute SHOW ALL SLAVES STATUS multiple times
    # Collect unique results (deduplicate by server_id or connection_name)
    # Return combined results
```

### Option 2: Use SkySQL API to Discover Replicas (Not Needed)

**Status**: Not implementing - workaround approach is sufficient

**Reason**: 
- SkySQL has maximum of 5 replicas
- Executing 10 times ensures we hit all replicas
- No need for API complexity for Phase 1

## Recommended Implementation Plan

### Phase 1: Basic Implementation (Current Plan)

**Use Option 1** - The existing workaround approach:

1. **Create tool**: `get_all_replica_status()`
   - Execute `SHOW ALL SLAVES STATUS` multiple times (default: 10)
   - **SkySQL constraint**: Maximum 5 replicas, so 10 executions ensures coverage
   - Collect and deduplicate results
   - Return combined status from all replicas found

2. **Deduplication Strategy**:
   - Use `Connection_name` or `Server_id` to identify unique replicas
   - If both are available, prefer `Connection_name` (more reliable)
   - Store results in a dict keyed by identifier
   - Maximum expected: 5 unique replicas (SkySQL limit)

3. **Handle Edge Cases**:
   - If no results: Service might not have replication configured
   - If only one result: Might be hitting same replica, or only one replica exists
   - If 2-5 results: Normal, we're getting multiple replicas
   - If more than 5 results: Unexpected (shouldn't happen in SkySQL), but handle gracefully

4. **For Master Status**:
   - Use `SHOW MASTER STATUS` (single execution, will hit primary)
   - Or use `SHOW ALL SLAVES STATUS` and look for empty results (indicates primary)

## Implementation Details

### Tool: get_all_replica_status()

```python
@function_tool
def get_all_replica_status(
    max_executions: int = 10,
) -> dict[str, Any]:
    """
    Get replication status from all replicas in a SkySQL service.
    
    This function works around MaxScale load balancing by executing
    SHOW ALL SLAVES STATUS multiple times. Each execution may be
    routed to a different replica by MaxScale's round-robin algorithm.
    
    Args:
        max_executions: Number of times to execute the query (default: 10)
                       Increase this if you have many replicas
    
    Returns:
        Dictionary with:
        - 'replicas': List of replica status dictionaries (one per unique replica)
        - 'count': Number of unique replicas found
        - 'executions': Number of times query was executed
        - 'note': Information about the approach used
    """
    from ...common.db_client import run_readonly_query
    
    all_results = []
    seen_replicas = {}  # Keyed by Connection_name or Server_id
    
    # Execute multiple times to hit different replicas
    for i in range(max_executions):
        try:
            # SHOW ALL SLAVES STATUS returns one row per replica on that server
            # In a multi-source setup, one server can have multiple replica connections
            results = run_readonly_query(
                sql="SHOW ALL SLAVES STATUS",
                max_rows=100,  # Allow multiple rows per execution
                timeout_seconds=10,
            )
            
            for row in results:
                # Use Connection_name as primary identifier (if available)
                # Fall back to Server_id if Connection_name not available
                identifier = row.get('Connection_name') or row.get('Server_id') or f"replica_{i}"
                
                # Only keep first occurrence of each replica
                if identifier not in seen_replicas:
                    seen_replicas[identifier] = row
                    all_results.append(row)
        
        except Exception as e:
            # Log error but continue with next execution
            logger.warning(f"Execution {i+1} failed: {e}")
            continue
    
    return {
        "replicas": list(seen_replicas.values()),
        "count": len(seen_replicas),
        "executions": max_executions,
        "max_expected": 5,  # SkySQL maximum
        "note": f"Executed SHOW ALL SLAVES STATUS {max_executions} times via MaxScale. "
                f"Found {len(seen_replicas)} unique replicas (SkySQL max: 5). "
                f"Note: Results may vary due to MaxScale load balancing."
    }
```

### Tool: get_master_status()

```python
@function_tool
def get_master_status() -> dict[str, Any]:
    """
    Get master/replication source status.
    
    In SkySQL/MaxScale environment, this will hit the primary server.
    
    Returns:
        Dictionary with master status information
    """
    from ...common.db_client import run_readonly_query
    
    results = run_readonly_query(
        sql="SHOW MASTER STATUS",
        max_rows=10,
        timeout_seconds=10,
    )
    
    if not results:
        return {
            "available": False,
            "note": "SHOW MASTER STATUS returned no results. This server may not be configured as a master, or replication may not be enabled."
        }
    
    return {
        "available": True,
        "status": results[0] if results else None,
    }
```

### Tool: get_replication_configuration()

```python
@function_tool
def get_replication_configuration() -> dict[str, Any]:
    """
    Get replication-related configuration variables.
    
    Returns:
        Dictionary with replication configuration
    """
    from ...common.db_client import run_readonly_query
    
    # Get replication variables
    variables = run_readonly_query(
        sql="""
        SELECT VARIABLE_NAME, VARIABLE_VALUE
        FROM information_schema.GLOBAL_VARIABLES
        WHERE VARIABLE_NAME IN (
            'server_id',
            'log_bin',
            'binlog_format',
            'sync_binlog',
            'expire_logs_days',
            'gtid_domain_id',
            'gtid_strict_mode',
            'read_only',
            'super_read_only'
        )
        """,
        max_rows=50,
        timeout_seconds=10,
    )
    
    config = {v['VARIABLE_NAME']: v['VARIABLE_VALUE'] for v in variables}
    
    return {
        "configuration": config,
        "is_replica": config.get('read_only') == 'ON' or config.get('super_read_only') == 'ON',
        "is_master": config.get('log_bin') == 'ON',
        "gtid_enabled": config.get('gtid_domain_id') is not None and config.get('gtid_domain_id') != '0',
    }
```

## Handling Non-SkySQL Environments

For non-SkySQL environments (direct connections):

1. **Single Connection**: If connecting directly to a specific server
   - Use `SHOW REPLICA STATUS` / `SHOW SLAVE STATUS` directly
   - Use `SHOW MASTER STATUS` directly
   - No need for multiple executions

2. **Multiple Connections**: If we have connection info for each server
   - Connect to each server individually
   - Get status from each
   - Combine results

## Detection Strategy

The agent should detect the environment:

```python
def is_skysql_environment(host: str) -> bool:
    """Check if we're in a SkySQL environment."""
    return 'skysql.com' in host.lower()

def should_use_maxscale_workaround(host: str) -> bool:
    """Determine if we should use MaxScale workaround."""
    return is_skysql_environment(host)
```

## Summary

**For Phase 1 (Initial Implementation)**:
- ✅ Use `SHOW ALL SLAVES STATUS` with multiple executions (workaround)
- ✅ Execute 10 times by default (sufficient for SkySQL max of 5 replicas)
- ✅ Deduplicate results by `Connection_name` or `Server_id`
- ✅ Use `SHOW MASTER STATUS` for primary status
- ✅ Document limitations clearly
- ✅ No SkySQL API integration needed (workaround is sufficient)

**Key Points**:
- MaxScale load balancing makes this challenging
- The workaround is proven to work (from existing codebase)
- **SkySQL constraint**: Maximum 5 replicas, so 10 executions ensures we hit all
- For SkySQL, this workaround approach is sufficient
- For non-SkySQL, we can connect directly to each server if connection info available

