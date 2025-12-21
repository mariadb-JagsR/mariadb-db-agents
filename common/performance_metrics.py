# src/common/performance_metrics.py
"""
Performance Schema metrics utilities for query analysis.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .db_client import run_readonly_query

logger = logging.getLogger(__name__)


def check_performance_schema_enabled() -> bool:
    """
    Check if Performance Schema is enabled.
    
    Returns:
        True if Performance Schema is enabled, False otherwise
    """
    try:
        sql = "SELECT @@performance_schema"
        result = run_readonly_query(
            sql=sql,
            max_rows=1,
            timeout_seconds=5,
            database=None,
        )
        if result and len(result) > 0:
            return bool(result[0].get("@@performance_schema", 0))
        return False
    except Exception as e:
        logger.debug(f"Performance Schema check failed: {e}")
        return False


def get_statement_metrics_by_thread_id(
    thread_id: int,
) -> Optional[Dict[str, Any]]:
    """
    Get Performance Schema statement metrics for a specific thread ID.
    
    Args:
        thread_id: Thread/connection ID from processlist
        
    Returns:
        Dictionary with performance metrics or None if not available
    """
    if not check_performance_schema_enabled():
        return None
    
    try:
        # First, get the performance_schema thread_id from processlist ID
        # thread_id is an integer, safe to use directly
        sql = f"""
            SELECT thread_id 
            FROM performance_schema.threads 
            WHERE processlist_id = {int(thread_id)}
            LIMIT 1
        """
        thread_result = run_readonly_query(
            sql=sql,
            max_rows=1,
            timeout_seconds=5,
            database=None,
        )
        
        if not thread_result or len(thread_result) == 0:
            return None
        
        perf_thread_id = thread_result[0].get("thread_id")
        if not perf_thread_id:
            return None
        
        # Get statement metrics for this thread
        # perf_thread_id is from our query result, safe to use
        # Note: MariaDB doesn't have cpu_time column, so we calculate approximate CPU time
        # as TIMER_WAIT - LOCK_TIME (time not spent waiting for locks)
        sql = f"""
            SELECT 
                SQL_TEXT as sql_text,
                TIMER_START as timer_start,
                TIMER_END as timer_end,
                TIMER_WAIT / 1000000000000 as timer_wait_sec,
                LOCK_TIME / 1000000000000 as lock_time_sec,
                (TIMER_WAIT - LOCK_TIME) / 1000000000000 as approximate_cpu_time_sec,
                ROWS_EXAMINED as rows_examined,
                ROWS_SENT as rows_sent,
                ROWS_AFFECTED as rows_affected,
                CREATED_TMP_TABLES as created_tmp_tables,
                CREATED_TMP_DISK_TABLES as created_tmp_disk_tables,
                SELECT_SCAN as select_scan,
                SELECT_FULL_JOIN as select_full_join,
                SELECT_FULL_RANGE_JOIN as select_full_range_join,
                SELECT_RANGE as select_range,
                SELECT_RANGE_CHECK as select_range_check,
                SORT_MERGE_PASSES as sort_merge_passes,
                SORT_RANGE as sort_range,
                SORT_ROWS as sort_rows,
                SORT_SCAN as sort_scan,
                NO_INDEX_USED as no_index_used,
                NO_GOOD_INDEX_USED as no_good_index_used
            FROM performance_schema.events_statements_current
            WHERE THREAD_ID = {int(perf_thread_id)}
            LIMIT 1
        """
        
        result = run_readonly_query(
            sql=sql,
            max_rows=1,
            timeout_seconds=5,
            database=None,
        )
        
        if result and len(result) > 0:
            return result[0]
        return None
        
    except Exception as e:
        logger.debug(f"Failed to get statement metrics for thread {thread_id}: {e}")
        return None


def get_statement_metrics_by_digest(
    query_digest: str,
    database: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Get Performance Schema statement metrics aggregated by query digest.
    
    Args:
        query_digest: Query digest (normalized SQL pattern)
        database: Optional database name to filter by
        
    Returns:
        Dictionary with aggregated performance metrics or None if not available
    """
    if not check_performance_schema_enabled():
        return None
    
    try:
        # Escape single quotes in query_digest to prevent SQL injection
        safe_digest = query_digest[:50].replace("'", "''")
        conditions = [f"digest_text LIKE '%{safe_digest}%'"]
        if database:
            # Escape single quotes in database name
            safe_db = database.replace("'", "''")
            conditions.append(f"schema_name = '{safe_db}'")
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        # Check if LOCK_TIME column exists (MariaDB version compatibility)
        # Some versions use SUM_LOCK_TIME/AVG_LOCK_TIME, others may not have it
        try:
            # Try to detect if LOCK_TIME columns exist
            check_sql = """
                SELECT COLUMN_NAME 
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = 'performance_schema' 
                  AND TABLE_NAME = 'events_statements_summary_by_digest'
                  AND COLUMN_NAME IN ('SUM_LOCK_TIME', 'AVG_LOCK_TIME')
                LIMIT 1
            """
            lock_time_check = run_readonly_query(sql=check_sql, max_rows=1, timeout_seconds=2, database=None)
            has_lock_time = lock_time_check and len(lock_time_check) > 0
        except:
            has_lock_time = False
        
        # Build query with conditional lock time columns
        if has_lock_time:
            lock_time_cols = """
                SUM_LOCK_TIME / 1000000000000 as total_lock_time_sec,
                AVG_LOCK_TIME / 1000000000000 as avg_lock_time_sec,
                (SUM_TIMER_WAIT - SUM_LOCK_TIME) / 1000000000000 as total_approximate_cpu_time_sec,
                (AVG_TIMER_WAIT - AVG_LOCK_TIME) / 1000000000000 as avg_approximate_cpu_time_sec,
            """
        else:
            lock_time_cols = """
                NULL as total_lock_time_sec,
                NULL as avg_lock_time_sec,
                SUM_TIMER_WAIT / 1000000000000 as total_approximate_cpu_time_sec,
                AVG_TIMER_WAIT / 1000000000000 as avg_approximate_cpu_time_sec,
            """
        
        sql = f"""
            SELECT 
                DIGEST_TEXT as digest_text,
                COUNT_STAR as exec_count,
                SUM_TIMER_WAIT / 1000000000000 as total_timer_wait_sec,
                AVG_TIMER_WAIT / 1000000000000 as avg_timer_wait_sec,
                {lock_time_cols}
                SUM_ROWS_EXAMINED as total_rows_examined,
                AVG_ROWS_EXAMINED as avg_rows_examined,
                SUM_ROWS_SENT as total_rows_sent,
                AVG_ROWS_SENT as avg_rows_sent,
                SUM_ROWS_AFFECTED as total_rows_affected,
                SUM_CREATED_TMP_TABLES as total_created_tmp_tables,
                SUM_CREATED_TMP_DISK_TABLES as total_created_tmp_disk_tables,
                SUM_SELECT_SCAN as total_select_scan,
                SUM_SELECT_FULL_JOIN as total_select_full_join,
                SUM_NO_INDEX_USED as total_no_index_used,
                SUM_NO_GOOD_INDEX_USED as total_no_good_index_used
            FROM performance_schema.events_statements_summary_by_digest
            {where_clause}
            ORDER BY SUM_TIMER_WAIT DESC
            LIMIT 1
        """
        
        result = run_readonly_query(
            sql=sql,
            max_rows=1,
            timeout_seconds=5,
            database=None,
        )
        
        if result and len(result) > 0:
            return result[0]
        return None
        
    except Exception as e:
        logger.debug(f"Failed to get statement metrics by digest: {e}")
        return None


def get_buffer_pool_stats() -> Optional[Dict[str, Any]]:
    """
    Get InnoDB buffer pool statistics.
    
    Returns:
        Dictionary with buffer pool statistics or None if not available
    """
    try:
        sql = """
            SELECT 
                POOL_ID,
                POOL_SIZE,
                FREE_BUFFERS,
                DATABASE_PAGES,
                OLD_DATABASE_PAGES,
                MODIFIED_DATABASE_PAGES,
                PENDING_DECOMPRESS,
                PENDING_READS,
                PENDING_FLUSH_LRU,
                PENDING_FLUSH_LIST,
                PAGES_MADE_YOUNG,
                PAGES_NOT_MADE_YOUNG,
                PAGES_MADE_YOUNG_RATE,
                PAGES_MADE_NOT_YOUNG_RATE,
                NUMBER_PAGES_READ,
                NUMBER_PAGES_CREATED,
                NUMBER_PAGES_WRITTEN,
                PAGES_READ_RATE,
                PAGES_CREATE_RATE,
                PAGES_WRITTEN_RATE,
                NUMBER_PAGES_GET,
                HIT_RATE,
                YOUNG_MAKE_PER_THOUSAND_GETS,
                NOT_YOUNG_MAKE_PER_THOUSAND_GETS,
                NUMBER_PAGES_READ_AHEAD,
                NUMBER_READ_AHEAD_EVICTED,
                READ_AHEAD_RATE,
                READ_AHEAD_EVICTED_RATE,
                LRU_IO_TOTAL,
                LRU_IO_CURRENT,
                UNCOMPRESS_TOTAL,
                UNCOMPRESS_CURRENT
            FROM information_schema.INNODB_BUFFER_POOL_STATS
        """
        
        result = run_readonly_query(
            sql=sql,
            max_rows=10,
            timeout_seconds=5,
            database=None,
        )
        
        if result and len(result) > 0:
            # Aggregate stats if multiple buffer pools
            if len(result) == 1:
                return result[0]
            else:
                # Sum up values for multiple buffer pools
                aggregated = {}
                for key in result[0].keys():
                    if key == "POOL_ID":
                        aggregated[key] = "ALL"
                    elif isinstance(result[0][key], (int, float)):
                        aggregated[key] = sum(row.get(key, 0) or 0 for row in result)
                    else:
                        aggregated[key] = result[0][key]
                return aggregated
        return None
        
    except Exception as e:
        logger.debug(f"Failed to get buffer pool stats: {e}")
        return None

