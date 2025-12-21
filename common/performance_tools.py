# src/common/performance_tools.py
"""
Performance Schema tools for agents to query performance metrics.
"""

from __future__ import annotations

from typing import Any
from agents import function_tool
from .db_client import run_readonly_query
from .performance_metrics import (
    check_performance_schema_enabled,
    get_statement_metrics_by_thread_id,
    get_statement_metrics_by_digest,
    get_buffer_pool_stats,
)


@function_tool
def get_performance_metrics_for_thread(
    thread_id: int,
) -> dict[str, Any]:
    """
    Get Performance Schema metrics for a specific running query thread.
    
    Use this to get detailed performance metrics for queries currently running.
    This provides CPU time, lock wait time, I/O statistics, and more.
    
    Args:
        thread_id: Thread/connection ID from processlist (ID column)
        
    Returns:
        Dictionary with:
        - available: True if Performance Schema is enabled and metrics found
        - metrics: Dictionary containing:
          - cpu_time_sec: CPU time spent executing the query
          - lock_time_sec: Time spent waiting for locks
          - timer_wait_sec: Total execution time (wall clock)
          - rows_examined: Rows examined
          - rows_sent: Rows returned
          - created_tmp_tables: Temporary tables created
          - created_tmp_disk_tables: Temporary tables created on disk
          - no_index_used: Whether indexes were used
          - And other performance metrics
        - message: Error message if metrics unavailable
    """
    if not check_performance_schema_enabled():
        return {
            "available": False,
            "metrics": None,
            "message": "Performance Schema is not enabled on this database instance.",
        }
    
    metrics = get_statement_metrics_by_thread_id(thread_id)
    
    if metrics:
        return {
            "available": True,
            "metrics": metrics,
            "message": None,
        }
    else:
        return {
            "available": False,
            "metrics": None,
            "message": f"No Performance Schema metrics found for thread {thread_id}. The query may have completed or Performance Schema data is not available.",
        }


@function_tool
def get_performance_metrics_for_query(
    query_text: str,
    database: str | None = None,
) -> dict[str, Any]:
    """
    Get Performance Schema metrics aggregated by query digest (normalized query pattern).
    
    Use this to get aggregated performance metrics for query patterns from slow query log.
    This provides CPU time, lock wait time, I/O statistics averaged across all executions.
    
    Args:
        query_text: SQL query text (will be matched against normalized digest)
        database: Optional database name to filter by
        
    Returns:
        Dictionary with:
        - available: True if Performance Schema is enabled and metrics found
        - metrics: Dictionary containing:
          - exec_count: Number of times this query pattern executed
          - avg_cpu_time_sec: Average CPU time per execution
          - total_cpu_time_sec: Total CPU time across all executions
          - avg_lock_time_sec: Average lock wait time per execution
          - avg_timer_wait_sec: Average execution time (wall clock)
          - avg_rows_examined: Average rows examined
          - avg_rows_sent: Average rows returned
          - total_no_index_used: Count of executions without index usage
          - And other aggregated performance metrics
        - message: Error message if metrics unavailable
    """
    if not check_performance_schema_enabled():
        return {
            "available": False,
            "metrics": None,
            "message": "Performance Schema is not enabled on this database instance.",
        }
    
    # Extract a portion of the query for matching (first 50 chars)
    query_sample = query_text.strip()[:50] if query_text else ""
    
    metrics = get_statement_metrics_by_digest(query_sample, database)
    
    if metrics:
        return {
            "available": True,
            "metrics": metrics,
            "message": None,
        }
    else:
        return {
            "available": False,
            "metrics": None,
            "message": f"No Performance Schema metrics found for query pattern. The query may not have been executed recently or Performance Schema data is not available.",
        }


@function_tool
def get_buffer_pool_statistics() -> dict[str, Any]:
    """
    Get InnoDB buffer pool statistics including cache hit ratio.
    
    Use this to understand overall database cache performance and whether
    queries are hitting disk vs memory.
    
    Returns:
        Dictionary with:
        - available: True if buffer pool stats are available
        - stats: Dictionary containing:
          - HIT_RATE: Buffer pool hit ratio (0-1, higher is better)
          - PAGES_READ: Total pages read from disk
          - PAGES_WRITTEN: Total pages written to disk
          - DATABASE_PAGES: Pages currently in buffer pool
          - FREE_BUFFERS: Free buffer pages
          - PAGES_MADE_YOUNG: Pages moved to young sublist
          - And other buffer pool statistics
        - message: Error message if stats unavailable
    """
    stats = get_buffer_pool_stats()
    
    if stats:
        return {
            "available": True,
            "stats": stats,
            "message": None,
        }
    else:
        return {
            "available": False,
            "stats": None,
            "message": "Buffer pool statistics are not available. This may be a non-InnoDB engine or statistics are not accessible.",
        }

