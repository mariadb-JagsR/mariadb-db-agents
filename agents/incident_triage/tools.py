# agents/incident_triage/tools.py
from __future__ import annotations

from typing import Any
from agents import function_tool
from ...common.db_client import run_readonly_query, tail_error_log_file
from ...common.performance_tools import get_buffer_pool_statistics
from ...common.sys_schema_tools import (
    get_sys_metrics,
    get_sys_innodb_lock_waits,
    get_sys_processlist,
    get_sys_schema_table_lock_waits,
    get_sys_io_global_by_file_by_latency,
    get_sys_statement_analysis,
)


@function_tool
def execute_sql(
    sql: str,
    max_rows: int = 1000,
    timeout_seconds: int = 5,
    database: str | None = None,
) -> dict[str, Any]:
    """
    Execute a read-only SQL query against a MariaDB / MariaDB Cloud instance.
    
    Database connection is configured via environment variables (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_DATABASE).

    Use this to:
    - Check global status and variables
    - Query SHOW ENGINE INNODB STATUS
    - Check replication status
    - Query processlist for blocking queries
    - Get system metrics

    Args:
        sql: Read-only SQL statement to execute
        max_rows: Maximum number of rows to return (default: 1000)
        timeout_seconds: Query timeout in seconds (default: 5)
        database: Optional database name to use

    Returns:
        Dictionary with 'rows' key containing the query results
    """
    rows = run_readonly_query(
        sql=sql,
        max_rows=max_rows,
        timeout_seconds=timeout_seconds,
        database=database,
    )
    return {"rows": rows}


@function_tool
def read_error_log(
    service_id: str | None = None,
    path: str | None = None,
    max_bytes: int = 1_000_000,
    tail_lines: int = 5000,
    extract_patterns: bool = True,
    max_patterns: int = 20,
) -> dict[str, Any]:
    """
    Read MariaDB error log and extract error patterns.
    
    This tool reads error logs and groups similar errors together to avoid
    sending huge log files to the LLM. It normalizes error messages by
    replacing timestamps, PIDs, connection IDs, and specific database/table names.
    
    Supports two access methods:
    1. SkySQL API: Provide service_id to fetch logs via API (or set SKYSQL_SERVICE_ID env var)
    2. Local file: Provide path to read from filesystem (for development/testing)
    
    Args:
        service_id: Database service identifier (for SkySQL API access). 
                   If not provided, will check SKYSQL_SERVICE_ID environment variable.
        path: Absolute path to error log file (for local file access)
        max_bytes: Maximum bytes to read from end of log (default: 1_000_000)
        tail_lines: Approximate number of lines from end (default: 5000)
        extract_patterns: If True, extract and group error patterns (default: True)
        max_patterns: Maximum unique patterns to return (default: 20)
    
    Returns:
        Dictionary with:
        - patterns: List of error patterns (if extract_patterns=True)
          Each pattern has: pattern, count, severity, first_seen, last_seen, sample_message
        - content: Raw log content (if extract_patterns=False)
        - total_lines: Total lines processed
        - source: 'local_file' or 'skysql_api' or 'not_implemented'
    """
    import os
    
    # If service_id not provided, try environment variable
    if not service_id:
        service_id = os.getenv("SKYSQL_SERVICE_ID")
    
    result = tail_error_log_file(
        service_id=service_id,
        path=path,
        max_bytes=max_bytes,
        tail_lines=tail_lines,
        extract_patterns=extract_patterns,
        max_patterns=max_patterns,
    )
    return result

