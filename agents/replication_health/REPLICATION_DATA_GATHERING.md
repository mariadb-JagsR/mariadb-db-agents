# Replication Health Agent - Data Gathering Strategy

This document outlines how the Replication Health Agent will gather all relevant replication information from MariaDB.

## Overview

The Replication Health Agent needs to:
1. Detect if replication is configured
2. Gather replication status from all replicas
3. Identify replication lag
4. Detect replication failures
5. Analyze replication delay trends
6. Identify queries causing replication lag
7. Check GTID consistency
8. Propose resolution paths

---

## 1. Detecting Replication Configuration

### Check if Replication is Configured

**Query 1: Check if this is a replica**
```sql
SHOW SLAVE STATUS;
-- OR (MariaDB 10.5+)
SHOW REPLICA STATUS;
```

**Expected Results:**
- If replication is configured: Returns rows with replication status
- If not configured: Returns empty result set

**Key Fields to Check:**
- `Slave_IO_Running` / `Replica_IO_Running` - Is IO thread running?
- `Slave_SQL_Running` / `Replica_SQL_Running` - Is SQL thread running?
- `Master_Host` / `Source_Host` - Master/replica host
- `Master_Port` / `Source_Port` - Master/replica port

**Query 2: Check if this is a master**
```sql
SHOW MASTER STATUS;
```

**Expected Results:**
- If master is configured: Returns binlog position and file
- If not configured: Returns empty result set

**Key Fields:**
- `File` - Current binlog file
- `Position` - Current binlog position
- `Binlog_Do_DB` - Databases to replicate
- `Binlog_Ignore_DB` - Databases to ignore

**Query 3: Check replication configuration from information_schema**
```sql
-- Check if replication is enabled
SELECT VARIABLE_VALUE 
FROM information_schema.GLOBAL_VARIABLES 
WHERE VARIABLE_NAME = 'server_id';

-- Check if binlog is enabled
SELECT VARIABLE_VALUE 
FROM information_schema.GLOBAL_VARIABLES 
WHERE VARIABLE_NAME = 'log_bin';
```

---

## 2. Gathering Replication Status (Replica Side)

### Primary Status Query

**Query: SHOW REPLICA STATUS (MariaDB 10.5+) or SHOW SLAVE STATUS (older)**
```sql
SHOW REPLICA STATUS\G
-- OR
SHOW SLAVE STATUS\G
```

**Critical Fields to Extract:**

**Connection Status:**
- `Replica_IO_Running` / `Slave_IO_Running` - IO thread state (Yes/No/Connecting)
- `Replica_SQL_Running` / `Slave_SQL_Running` - SQL thread state (Yes/No)
- `Replica_IO_State` / `Slave_IO_State` - Current IO thread state description

**Lag Metrics:**
- `Seconds_Behind_Master` / `Seconds_Behind_Source` - **Primary lag indicator** (seconds)
- `Master_Log_File` / `Source_Log_File` - Last read binlog file
- `Read_Master_Log_Pos` / `Read_Source_Log_Pos` - Last read position
- `Relay_Master_Log_File` / `Relay_Source_Log_File` - Last executed binlog file
- `Exec_Master_Log_Pos` / `Exec_Source_Log_Pos` - Last executed position

**Error Information:**
- `Last_IO_Error` / `Last_IO_Error_Timestamp` - Last IO thread error
- `Last_SQL_Error` / `Last_SQL_Error_Timestamp` - Last SQL thread error
- `Last_IO_Errno` - IO error number
- `Last_SQL_Errno` - SQL error number

**GTID Information:**
- `Using_Gtid` - Is GTID enabled? (Current_Pos/Slave_Pos/No)
- `Gtid_IO_Pos` - Current GTID position
- `Gtid_Slave_Pos` - Slave GTID position

**Connection Information:**
- `Master_Host` / `Source_Host` - Master hostname
- `Master_Port` / `Source_Port` - Master port
- `Master_User` / `Source_User` - Replication user
- `Master_Log_File` / `Source_Log_File` - Current binlog file being read

**Relay Log Information:**
- `Relay_Log_File` - Current relay log file
- `Relay_Log_Pos` - Current relay log position
- `Relay_Master_Log_File` / `Relay_Source_Log_File` - Master binlog file corresponding to relay log

**Replication Filters:**
- `Replicate_Do_DB` / `Replicate_Ignore_DB` - Database filters
- `Replicate_Do_Table` / `Replicate_Ignore_Table` - Table filters
- `Replicate_Wild_Do_Table` / `Replicate_Wild_Ignore_Table` - Wildcard table filters

### Alternative: Query information_schema (if available)

**Query: Check replication status from information_schema**
```sql
-- MariaDB 10.5+ has replication status in information_schema
SELECT * 
FROM information_schema.REPLICA_STATUS;
-- OR
SELECT * 
FROM information_schema.SLAVE_STATUS;
```

**Note:** This may not be available in all MariaDB versions. SHOW REPLICA STATUS is more reliable.

---

## 3. Gathering Master Status

### Primary Master Status Query

**Query: SHOW MASTER STATUS**
```sql
SHOW MASTER STATUS;
```

**Key Fields:**
- `File` - Current binlog file name
- `Position` - Current binlog position
- `Binlog_Do_DB` - Databases to replicate
- `Binlog_Ignore_DB` - Databases to ignore
- `Executed_Gtid_Set` - GTID set that has been executed (if GTID enabled)

### Check Connected Replicas

**Query: SHOW SLAVE HOSTS (or SHOW REPLICA HOSTS)**
```sql
SHOW SLAVE HOSTS;
-- OR
SHOW REPLICA HOSTS;
```

**Key Fields:**
- `Server_id` - Replica server ID
- `Host` - Replica hostname
- `Port` - Replica port
- `Master_id` / `Source_id` - Master server ID
- `Slave_UUID` / `Replica_UUID` - Replica UUID

**Note:** This only shows replicas that have `report_host` configured.

### Check Binlog Files

**Query: SHOW BINARY LOGS**
```sql
SHOW BINARY LOGS;
```

**Key Fields:**
- `Log_name` - Binlog file name
- `File_size` - File size in bytes
- `Encrypted` - Whether binlog is encrypted

**Use Case:** 
- Check binlog retention
- Estimate replication lag by comparing file sizes
- Check if binlogs are being purged

---

## 4. GTID (Global Transaction ID) Information

### Check GTID Status

**Query 1: Check if GTID is enabled**
```sql
SELECT VARIABLE_VALUE 
FROM information_schema.GLOBAL_VARIABLES 
WHERE VARIABLE_NAME = 'gtid_domain_id';
-- OR
SHOW VARIABLES LIKE 'gtid%';
```

**Query 2: Get current GTID position (Master)**
```sql
SHOW MASTER STATUS;
-- Check Executed_Gtid_Set field
```

**Query 3: Get current GTID position (Replica)**
```sql
SHOW REPLICA STATUS;
-- Check Gtid_IO_Pos and Gtid_Slave_Pos fields
```

**Query 4: Get GTID list (if available)**
```sql
SELECT * FROM mysql.gtid_slave_pos;
-- OR
SELECT * FROM mysql.gtid_pos;
```

**Use Case:**
- Verify GTID consistency across replicas
- Check if GTID is properly configured
- Identify GTID gaps

---

## 5. Replication Lag Analysis

### Primary Lag Metric

**From SHOW REPLICA STATUS:**
- `Seconds_Behind_Master` / `Seconds_Behind_Source` - **Most important lag metric**

**Interpretation:**
- `0` or `NULL` - No lag (or not a replica)
- `> 0` - Lag in seconds
- `NULL` - Could mean:
  - Not a replica
  - IO thread not running
  - Connection issues

### Detailed Lag Analysis

**Query: Compare binlog positions**
```sql
-- On Replica: Get current position
SHOW REPLICA STATUS;
-- Extract: Read_Master_Log_Pos, Master_Log_File

-- On Master: Get current position  
SHOW MASTER STATUS;
-- Extract: Position, File

-- Calculate lag by comparing positions
```

**Query: Check relay log lag**
```sql
SHOW REPLICA STATUS;
-- Check:
-- Relay_Master_Log_File vs Master_Log_File
-- Exec_Master_Log_Pos vs Read_Master_Log_Pos
```

### Performance Schema Replication Metrics (if available)

**Query: Check replication lag from Performance Schema**
```sql
SELECT * 
FROM performance_schema.replication_connection_status;

SELECT * 
FROM performance_schema.replication_applier_status;

SELECT * 
FROM performance_schema.replication_applier_status_by_coordinator;

SELECT * 
FROM performance_schema.replication_applier_status_by_worker;
```

**Key Fields:**
- `THREAD_ID` - Replication thread ID
- `SERVICE_STATE` - Thread state (ON/OFF)
- `COUNT_TRANSACTIONS_IN_QUEUE` - Transactions waiting
- `COUNT_TRANSACTIONS_CHECKED` - Transactions processed
- `COUNT_CONFLICTS` - Conflicts detected
- `LAST_ERROR_NUMBER` - Last error number
- `LAST_ERROR_MESSAGE` - Last error message
- `LAST_ERROR_TIMESTAMP` - Last error timestamp

**Note:** Performance Schema replication tables may not be available in all MariaDB versions.

---

## 6. Detecting Replication Failures

### Check for Errors

**From SHOW REPLICA STATUS:**
- `Last_IO_Error` - Last IO thread error message
- `Last_IO_Error_Timestamp` - When IO error occurred
- `Last_IO_Errno` - IO error number
- `Last_SQL_Error` - Last SQL thread error message
- `Last_SQL_Error_Timestamp` - When SQL error occurred
- `Last_SQL_Errno` - SQL error number

**Common Error Codes:**
- `1032` - Row not found (replica has different data)
- `1062` - Duplicate entry (data inconsistency)
- `1594` - Relay log corruption
- `1595` - Relay log read error

### Check Thread Status

**From SHOW REPLICA STATUS:**
- `Replica_IO_Running` / `Slave_IO_Running`:
  - `Yes` - Running normally
  - `No` - Stopped (check Last_IO_Error)
  - `Connecting` - Trying to connect to master

- `Replica_SQL_Running` / `Slave_SQL_Running`:
  - `Yes` - Running normally
  - `No` - Stopped (check Last_SQL_Error)

### Check Connection Status

**Query: Check if replica can connect to master**
```sql
SHOW REPLICA STATUS;
-- Check Replica_IO_State:
-- "Waiting for master to send event" - Connected and waiting
-- "Connecting to master" - Connection in progress
-- "Reconnecting after a failed master event read" - Connection failed
```

---

## 7. Identifying Queries Causing Replication Lag

### Method 1: Check Slow Query Log on Replica

**Query: Check slow queries on replica**
```sql
-- If slow query log is in table
SELECT * 
FROM mysql.slow_log 
WHERE start_time >= NOW() - INTERVAL 1 HOUR
ORDER BY query_time DESC
LIMIT 10;
```

**Analysis:**
- Compare slow queries on replica vs master
- Identify queries that are slow only on replica
- Check for queries that don't use indexes

### Method 2: Check Processlist on Replica

**Query: Check current queries on replica**
```sql
SELECT * 
FROM information_schema.processlist 
WHERE command != 'Sleep'
ORDER BY time DESC;
```

**Analysis:**
- Identify long-running queries
- Check for queries blocking replication SQL thread
- Look for queries with high `time` value

### Method 3: Performance Schema Statement Analysis

**Query: Check statement statistics on replica**
```sql
SELECT 
    digest_text,
    count_star,
    sum_timer_wait / 1000000000000 as total_time_sec,
    avg_timer_wait / 1000000000000 as avg_time_sec,
    max_timer_wait / 1000000000000 as max_time_sec
FROM performance_schema.events_statements_summary_by_digest
WHERE digest_text LIKE '%INSERT%' OR digest_text LIKE '%UPDATE%' OR digest_text LIKE '%DELETE%'
ORDER BY sum_timer_wait DESC
LIMIT 20;
```

**Analysis:**
- Identify DML statements that are slow on replica
- Compare with master to see if replication is the bottleneck

### Method 4: Check Replication Applier Status

**Query: Check replication applier performance**
```sql
SELECT * 
FROM performance_schema.replication_applier_status_by_worker;
```

**Key Metrics:**
- `COUNT_TRANSACTIONS_IN_QUEUE` - Transactions waiting to be applied
- `COUNT_TRANSACTIONS_CHECKED` - Total transactions processed
- `COUNT_CONFLICTS` - Conflicts detected
- `LAST_ERROR_NUMBER` - Last error

---

## 8. Replication Topology Analysis

### Check Replication Chain

**Query: Identify all replicas**
```sql
-- On Master
SHOW SLAVE HOSTS;
-- OR
SHOW REPLICA HOSTS;
```

**Query: Check if this replica has its own replicas**
```sql
-- On each replica
SHOW SLAVE HOSTS;
-- OR  
SHOW REPLICA HOSTS;
```

**Use Case:**
- Map replication topology
- Identify cascading replication chains
- Check for replication loops

### Check Server IDs

**Query: Get server ID**
```sql
SELECT @@server_id;
-- OR
SELECT VARIABLE_VALUE 
FROM information_schema.GLOBAL_VARIABLES 
WHERE VARIABLE_NAME = 'server_id';
```

**Use Case:**
- Verify unique server IDs
- Identify server in replication chain

---

## 9. Binlog Analysis

### Check Binlog Events

**Query: Show recent binlog events**
```sql
SHOW BINLOG EVENTS 
IN 'mysql-bin.000001' 
FROM 4 
LIMIT 100;
```

**Key Information:**
- Event types (Query, Write_rows, Update_rows, Delete_rows, etc.)
- Database and table names
- Timestamps
- GTID (if enabled)

**Use Case:**
- Analyze what's being replicated
- Identify large transactions
- Check for problematic events

### Check Binlog Size and Retention

**Query: Check binlog files**
```sql
SHOW BINARY LOGS;
```

**Analysis:**
- Total binlog size
- Number of binlog files
- Check retention settings

**Query: Check binlog retention settings**
```sql
SHOW VARIABLES LIKE 'expire_logs_days';
-- OR
SELECT VARIABLE_VALUE 
FROM information_schema.GLOBAL_VARIABLES 
WHERE VARIABLE_NAME = 'expire_logs_days';
```

---

## 10. Replication Configuration Analysis

### Check Replication Settings

**Query: Get replication-related variables**
```sql
SHOW VARIABLES LIKE '%replica%';
SHOW VARIABLES LIKE '%slave%';
SHOW VARIABLES LIKE '%binlog%';
SHOW VARIABLES LIKE '%gtid%';
```

**Key Variables:**
- `server_id` - Server identifier
- `log_bin` - Binlog enabled
- `binlog_format` - Binlog format (ROW/STATEMENT/MIXED)
- `sync_binlog` - Binlog sync frequency
- `expire_logs_days` - Binlog retention
- `relay_log` - Relay log file
- `relay_log_recovery` - Relay log recovery
- `read_only` - Read-only mode
- `super_read_only` - Super read-only mode
- `gtid_domain_id` - GTID domain ID
- `gtid_strict_mode` - GTID strict mode

---

## 11. Data Consistency Checks

### Check for Replication Filters

**Query: Check replication filters**
```sql
SHOW REPLICA STATUS;
-- Check:
-- Replicate_Do_DB
-- Replicate_Ignore_DB
-- Replicate_Do_Table
-- Replicate_Ignore_Table
```

**Use Case:**
- Verify replication filters are correct
- Check if filters are causing data inconsistencies

### Check Table Differences (if possible)

**Note:** This requires comparing master and replica, which may not be directly queryable.

**Query: Check table row counts (if accessible)**
```sql
-- On Master
SELECT 
    table_schema,
    table_name,
    table_rows
FROM information_schema.tables
WHERE table_schema NOT IN ('information_schema', 'mysql', 'performance_schema', 'sys')
ORDER BY table_rows DESC;

-- Compare with replica (if we have access)
```

---

## 12. Performance Schema Replication Tables (MariaDB 10.5+)

### Available Tables

1. **replication_connection_status**
   - Connection status to master
   - Last error information
   - Connection state

2. **replication_applier_status**
   - Overall applier status
   - Coordinator status

3. **replication_applier_status_by_coordinator**
   - Coordinator thread status
   - Transaction queue

4. **replication_applier_status_by_worker**
   - Worker thread status
   - Per-worker metrics

**Query: Get comprehensive replication status**
```sql
SELECT * FROM performance_schema.replication_connection_status;
SELECT * FROM performance_schema.replication_applier_status;
SELECT * FROM performance_schema.replication_applier_status_by_coordinator;
SELECT * FROM performance_schema.replication_applier_status_by_worker;
```

---

## Implementation Strategy

### Tools Needed

1. **execute_sql** - Run all the SHOW and SELECT queries above
2. **get_replication_status** - Wrapper for SHOW REPLICA STATUS (handles version differences)
3. **get_master_status** - Wrapper for SHOW MASTER STATUS
4. **get_replica_hosts** - Wrapper for SHOW SLAVE HOSTS / SHOW REPLICA HOSTS
5. **get_binlog_info** - Wrapper for SHOW BINARY LOGS
6. **get_gtid_status** - Extract and parse GTID information
7. **get_replication_variables** - Get replication-related configuration

### Data Flow

1. **Detection Phase:**
   - Check if replication is configured (SHOW REPLICA STATUS, SHOW MASTER STATUS)
   - Determine role (master, replica, both, neither)

2. **Status Gathering Phase:**
   - If replica: Get SHOW REPLICA STATUS
   - If master: Get SHOW MASTER STATUS, SHOW SLAVE HOSTS
   - Get replication variables
   - Get GTID status (if enabled)

3. **Analysis Phase:**
   - Calculate lag (Seconds_Behind_Master)
   - Check for errors (Last_IO_Error, Last_SQL_Error)
   - Check thread status (IO_Running, SQL_Running)
   - Analyze binlog positions
   - Check Performance Schema metrics (if available)

4. **Deep Dive Phase (if issues found):**
   - Check slow queries on replica
   - Check processlist for blocking queries
   - Analyze binlog events
   - Check replication filters

### Error Handling

- Handle version differences (SLAVE vs REPLICA terminology)
- Handle cases where replication is not configured
- Handle Performance Schema availability
- Handle GTID vs non-GTID setups
- Handle connection errors gracefully

---

## Example Queries for Common Scenarios

### Scenario 1: Check if Replication is Working

```sql
-- Step 1: Check if replica
SHOW REPLICA STATUS;

-- Step 2: Check key fields
-- Replica_IO_Running = 'Yes'
-- Replica_SQL_Running = 'Yes'  
-- Seconds_Behind_Master < 60 (or acceptable threshold)
-- Last_IO_Error = '' (empty)
-- Last_SQL_Error = '' (empty)
```

### Scenario 2: Identify Replication Lag

```sql
-- Get lag
SHOW REPLICA STATUS;
-- Extract: Seconds_Behind_Master

-- If lag is high, check what's causing it
SELECT * FROM information_schema.processlist WHERE command != 'Sleep' ORDER BY time DESC;
SELECT * FROM mysql.slow_log WHERE start_time >= NOW() - INTERVAL 1 HOUR ORDER BY query_time DESC LIMIT 10;
```

### Scenario 3: Check for Replication Errors

```sql
SHOW REPLICA STATUS;
-- Check:
-- Last_IO_Error (not empty = IO thread error)
-- Last_SQL_Error (not empty = SQL thread error)
-- Last_IO_Errno (error number)
-- Last_SQL_Errno (error number)
```

### Scenario 4: Verify GTID Consistency

```sql
-- On Master
SHOW MASTER STATUS;
-- Extract: Executed_Gtid_Set

-- On Replica
SHOW REPLICA STATUS;
-- Extract: Gtid_IO_Pos, Gtid_Slave_Pos

-- Compare to ensure consistency
```

---

## Summary

The Replication Health Agent will gather information through:

1. **SHOW commands** (primary method):
   - `SHOW REPLICA STATUS` / `SHOW SLAVE STATUS`
   - `SHOW MASTER STATUS`
   - `SHOW SLAVE HOSTS` / `SHOW REPLICA HOSTS`
   - `SHOW BINARY LOGS`
   - `SHOW BINLOG EVENTS`

2. **information_schema queries**:
   - `GLOBAL_VARIABLES` for configuration
   - `GLOBAL_STATUS` for status metrics
   - `REPLICA_STATUS` / `SLAVE_STATUS` (if available)

3. **Performance Schema** (if available):
   - Replication connection/applier status tables
   - Statement analysis for lag identification

4. **Error log analysis** (via existing Incident Triage tools):
   - Replication-related errors
   - Connection failures

This comprehensive approach ensures we can detect, analyze, and diagnose all replication issues.

