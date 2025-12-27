# common/sys_schema_tools.py
"""
Sys schema (Performance Schema views) tools for incident triage and real-time analysis.

The sys schema provides human-readable views over Performance Schema data,
making it ideal for incident triage and quick health checks.
"""

from __future__ import annotations

from typing import Any
from agents import function_tool
from .db_client import run_readonly_query
from .performance_metrics import check_performance_schema_enabled


@function_tool
def get_sys_metrics() -> dict[str, Any]:
    """
    Get system-wide metrics from SHOW STATUS and SHOW VARIABLES (avoids sys schema).
    
    This provides a comprehensive view of database health including:
    - Connection metrics
    - Query performance metrics
    - InnoDB metrics
    - Lock metrics
    - I/O metrics
    
    Returns:
        Dictionary with:
        - available: True if metrics are available
        - metrics: List of metric dictionaries with variable_name, variable_value, type
        - message: Error message if unavailable
    """
    try:
        # Use SHOW STATUS and SHOW VARIABLES instead of sys.metrics
        # Combine both into a unified metrics list
        sql = """
            SELECT 
                VARIABLE_NAME AS variable_name,
                VARIABLE_VALUE AS variable_value,
                'status' AS type
            FROM information_schema.GLOBAL_STATUS
            WHERE VARIABLE_NAME IN (
                'Threads_connected', 'Threads_running', 'Max_used_connections',
                'Questions', 'Queries', 'Slow_queries',
                'Innodb_row_lock_current_waits', 'Innodb_row_lock_time_avg',
                'Created_tmp_tables', 'Created_tmp_disk_tables',
                'Table_locks_waited', 'Aborted_connects', 'Connection_errors_max_connections'
            )
            UNION ALL
            SELECT 
                VARIABLE_NAME AS variable_name,
                VARIABLE_VALUE AS variable_value,
                'variable' AS type
            FROM information_schema.GLOBAL_VARIABLES
            WHERE VARIABLE_NAME IN (
                'max_connections', 'max_connect_errors',
                'innodb_buffer_pool_size', 'tmp_table_size', 'max_heap_table_size'
            )
            ORDER BY type, variable_name
        """
        
        rows = run_readonly_query(sql=sql, max_rows=200, database=None)
        
        return {
            "available": True,
            "metrics": rows,
            "source": "information_schema",
            "message": None,
        }
    except Exception as e:
        return {
            "available": False,
            "metrics": None,
            "source": None,
            "message": f"Error querying metrics: {str(e)}. Use SHOW STATUS and SHOW VARIABLES via execute_sql as fallback.",
        }


@function_tool
def get_sys_innodb_lock_waits() -> dict[str, Any]:
    """
    Get current InnoDB lock waits from multiple sources with automatic fallback.
    
    This shows which transactions are waiting for locks and which transactions
    are holding those locks. Critical for diagnosing lock contention incidents.
    
    **Tries multiple sources in order (with automatic fallback):**
    1. **information_schema.innodb_lock_waits** (always available in MariaDB) - Primary source
    2. **SHOW ENGINE INNODB STATUS** (via execute_sql) - Fallback if information_schema unavailable
    
    This function automatically handles cases where sys schema views are unavailable
    (permissions, not installed, etc.) by using the underlying Performance Schema or
    information_schema tables directly.
    
    Returns:
        Dictionary with:
        - available: True if any lock wait source is available
        - lock_waits: List of lock wait dictionaries with transaction and lock information
        - source: Which source was used ('performance_schema', 'information_schema', or 'sys')
        - message: Error message if all sources unavailable
    """
    # Skip performance_schema.data_lock_waits - doesn't exist in MariaDB
    # Go straight to information_schema.innodb_lock_waits
    
    # Try information_schema.innodb_lock_waits with innodb_trx (always available in MariaDB)
    try:
        # Use the proven query pattern that joins with innodb_trx for detailed transaction info
        sql = """
            SELECT 
                NOW() AS observed_at,
                r.trx_id AS waiting_trx_id,
                r.trx_mysql_thread_id AS waiting_pid,
                r.trx_query AS waiting_query,
                r.trx_started AS waiting_trx_started,
                TIMESTAMPDIFF(SECOND, r.trx_started, NOW()) AS waiting_trx_age_sec,
                b.trx_id AS blocking_trx_id,
                b.trx_mysql_thread_id AS blocking_pid,
                b.trx_query AS blocking_query,
                b.trx_started AS blocking_trx_started,
                TIMESTAMPDIFF(SECOND, b.trx_started, NOW()) AS blocking_trx_age_sec
            FROM information_schema.innodb_lock_waits w
            JOIN information_schema.innodb_trx r ON r.trx_id = w.requesting_trx_id
            JOIN information_schema.innodb_trx b ON b.trx_id = w.blocking_trx_id
            ORDER BY r.trx_started
            LIMIT 50
        """
        
        rows = run_readonly_query(sql=sql, max_rows=50, database=None)
        
        if rows:
            return {
                "available": True,
                "lock_waits": rows,
                "source": "information_schema",
                "message": None,
            }
    except Exception as e:
        # If the join fails, try a simpler query
        try:
            sql = """
                SELECT 
                    requesting_trx_id AS waiting_trx_id,
                    requested_lock_id,
                    blocking_trx_id,
                    blocking_lock_id
                FROM information_schema.innodb_lock_waits
                LIMIT 50
            """
            
            rows = run_readonly_query(sql=sql, max_rows=50, database=None)
            
            if rows:
                return {
                    "available": True,
                    "lock_waits": rows,
                    "source": "information_schema",
                    "message": None,
                }
        except Exception as e2:
            # All information_schema sources failed
            pass
    
    # All sources failed
    return {
        "available": False,
        "lock_waits": None,
        "source": None,
        "message": "Lock wait sources unavailable. Try SHOW ENGINE INNODB STATUS via execute_sql for lock information, or check SHOW STATUS LIKE 'Innodb_row_lock_current_waits'.",
    }


@function_tool
def get_sys_processlist() -> dict[str, Any]:
    """
    Get process list from information_schema.processlist (avoids sys schema).
    
    This uses information_schema.processlist directly, which is always available in MariaDB.
    For enhanced metrics with Performance Schema data, use execute_sql to query
    performance_schema.threads and performance_schema.events_statements_current.
    
    Returns:
        Dictionary with:
        - available: True if processlist is available
        - processes: List of process dictionaries with:
          - ID: Thread/connection ID
          - USER: User
          - HOST: Host
          - DB: Database
          - COMMAND: Command type
          - TIME: Execution time in seconds
          - STATE: Current state
          - INFO: Current SQL statement
        - message: Error message if unavailable
    """
    try:
        # Use information_schema.processlist directly - always available
        sql = """
            SELECT 
                ID,
                USER,
                HOST,
                DB,
                COMMAND,
                TIME,
                STATE,
                INFO
            FROM information_schema.processlist
            WHERE COMMAND != 'Sleep' OR TIME > 0
            ORDER BY TIME DESC
            LIMIT 100
        """
        
        rows = run_readonly_query(sql=sql, max_rows=100, database=None)
        
        return {
            "available": True,
            "processes": rows,
            "source": "information_schema",
            "message": None,
        }
    except Exception as e:
        error_msg = str(e)
        return {
            "available": False,
            "processes": None,
            "source": None,
            "message": f"information_schema.processlist unavailable: {error_msg}",
        }


@function_tool
def get_sys_schema_table_lock_waits() -> dict[str, Any]:
    """
    Get table-level lock waits using performance_schema.metadata_locks.
    
    This shows which queries are waiting for table-level locks (metadata locks).
    Important for diagnosing DDL-related blocking issues.
    
    Returns:
        Dictionary with:
        - available: True if Performance Schema is available
        - table_lock_waits: List of table lock wait dictionaries
        - message: Error message if unavailable
    """
    if not check_performance_schema_enabled():
        return {
            "available": False,
            "table_lock_waits": None,
            "message": "Performance Schema is not enabled. Use information_schema.processlist to find queries waiting for locks.",
        }
    
    try:
        # Use performance_schema.metadata_locks directly
        sql = """
            SELECT 
                ml.object_schema,
                ml.object_name,
                ml.object_type,
                ml.lock_type,
                ml.lock_duration,
                ml.lock_status,
                t.PROCESSLIST_ID AS waiting_pid,
                t.PROCESSLIST_USER AS waiting_user,
                t.PROCESSLIST_HOST AS waiting_host,
                t.PROCESSLIST_DB AS waiting_db,
                t.PROCESSLIST_COMMAND AS waiting_command,
                t.PROCESSLIST_TIME AS waiting_time,
                t.PROCESSLIST_STATE AS waiting_state,
                t.PROCESSLIST_INFO AS waiting_query
            FROM performance_schema.metadata_locks ml
            JOIN performance_schema.threads t ON ml.owner_thread_id = t.thread_id
            WHERE ml.lock_status = 'PENDING'
            ORDER BY t.PROCESSLIST_TIME DESC
            LIMIT 50
        """
        
        rows = run_readonly_query(sql=sql, max_rows=50, database=None)
        
        return {
            "available": True,
            "table_lock_waits": rows,
            "source": "performance_schema",
            "message": None,
        }
    except Exception as e:
        error_msg = str(e)
        fallback_msg = "Use information_schema.processlist to find long-running queries that might be waiting for table locks."
        return {
            "available": False,
            "table_lock_waits": None,
            "source": None,
            "message": f"performance_schema.metadata_locks unavailable: {error_msg}. {fallback_msg}",
        }


@function_tool
def get_sys_io_global_by_file_by_latency(limit: int = 20) -> dict[str, Any]:
    """
    Get I/O bottlenecks from performance_schema.file_summary_by_instance.
    
    This shows which files (tables/indexes) are causing the most I/O latency.
    Critical for identifying disk I/O bottlenecks during incidents.
    
    Args:
        limit: Maximum number of files to return (default: 20)
    
    Returns:
        Dictionary with:
        - available: True if Performance Schema is available
        - io_bottlenecks: List of I/O bottleneck dictionaries
        - message: Error message if unavailable
    """
    if not check_performance_schema_enabled():
        return {
            "available": False,
            "io_bottlenecks": None,
            "message": "Performance Schema is not enabled. Use SHOW STATUS LIKE 'Innodb_buffer_pool_reads' and buffer pool statistics as fallback.",
        }
    
    try:
        # Use performance_schema.file_summary_by_instance directly
        sql = f"""
            SELECT 
                file_name AS file,
                SUM(count_read + count_write + count_misc) AS total,
                SUM(sum_timer_read + sum_timer_write + sum_timer_misc) / 1000000000000 AS total_latency_sec,
                SUM(count_read) AS count_read,
                SUM(sum_timer_read) / 1000000000000 AS read_latency_sec,
                SUM(count_write) AS count_write,
                SUM(sum_timer_write) / 1000000000000 AS write_latency_sec,
                SUM(count_misc) AS count_misc,
                SUM(sum_timer_misc) / 1000000000000 AS misc_latency_sec
            FROM performance_schema.file_summary_by_instance
            GROUP BY file_name
            ORDER BY total_latency_sec DESC
            LIMIT {limit}
        """
        
        rows = run_readonly_query(sql=sql, max_rows=limit, database=None)
        
        return {
            "available": True,
            "io_bottlenecks": rows,
            "source": "performance_schema",
            "message": None,
        }
    except Exception as e:
        error_msg = str(e)
        fallback_msg = "Use SHOW STATUS LIKE 'Innodb_buffer_pool_reads' and buffer pool statistics as fallback."
        return {
            "available": False,
            "io_bottlenecks": None,
            "source": None,
            "message": f"performance_schema.file_summary_by_instance unavailable: {error_msg}. {fallback_msg}",
        }


@function_tool
def get_sys_statement_analysis(limit: int = 20) -> dict[str, Any]:
    """
    Get statement analysis from performance_schema.events_statements_summary_by_digest.
    
    This shows the most resource-intensive statements recently executed.
    Critical for identifying problematic queries during incidents.
    
    Args:
        limit: Maximum number of statements to return (default: 20)
    
    Returns:
        Dictionary with:
        - available: True if Performance Schema is available
        - statements: List of statement dictionaries with:
          - digest_text: Query pattern (normalized)
          - schema_name: Database
          - count_star: Execution count
          - sum_timer_wait: Total latency (picoseconds)
          - avg_timer_wait: Average latency (picoseconds)
          - max_timer_wait: Maximum latency (picoseconds)
          - sum_lock_time: Total lock wait time (picoseconds)
          - sum_rows_sent: Rows sent
          - sum_rows_examined: Rows examined
          - sum_created_tmp_tables: Temporary tables created
          - sum_created_tmp_disk_tables: Disk temp tables created
        - message: Error message if unavailable
    """
    if not check_performance_schema_enabled():
        return {
            "available": False,
            "statements": None,
            "message": "Performance Schema is not enabled. Use information_schema.processlist to find long-running queries, or query mysql.slow_log if available.",
        }
    
    try:
        # Use performance_schema.events_statements_summary_by_digest directly
        sql = f"""
            SELECT 
                DIGEST_TEXT AS query,
                SCHEMA_NAME AS db,
                COUNT_STAR AS exec_count,
                SUM_TIMER_WAIT / 1000000000000 AS total_latency_sec,
                AVG_TIMER_WAIT / 1000000000000 AS avg_latency_sec,
                MAX_TIMER_WAIT / 1000000000000 AS max_latency_sec,
                SUM_LOCK_TIME / 1000000000000 AS lock_latency_sec,
                SUM_ROWS_SENT AS rows_sent,
                SUM_ROWS_EXAMINED AS rows_examined,
                SUM_CREATED_TMP_TABLES AS tmp_tables,
                SUM_CREATED_TMP_DISK_TABLES AS tmp_disk_tables,
                SUM_NO_INDEX_USED AS full_scans
            FROM performance_schema.events_statements_summary_by_digest
            WHERE DIGEST_TEXT IS NOT NULL
            ORDER BY SUM_TIMER_WAIT DESC
            LIMIT {limit}
        """
        
        rows = run_readonly_query(sql=sql, max_rows=limit, database=None)
        
        return {
            "available": True,
            "statements": rows,
            "source": "performance_schema",
            "message": None,
        }
    except Exception as e:
        error_msg = str(e)
        fallback_msg = "Use information_schema.processlist to find long-running queries, or query mysql.slow_log if available."
        return {
            "available": False,
            "statements": None,
            "source": None,
            "message": f"performance_schema.events_statements_summary_by_digest unavailable: {error_msg}. {fallback_msg}",
        }

