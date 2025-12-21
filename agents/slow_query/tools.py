# agents/slow_query/tools.py
from __future__ import annotations

from typing import Any
from agents import function_tool
from ...common.db_client import run_readonly_query, tail_slow_log_file


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
    - Check slow_query_log configuration
    - Read mysql.slow_log table
    - Run EXPLAIN FORMAT=JSON
    - Inspect schema/index metadata
    - Query tables in any database (e.g., beer_reviews.beer_reviews_flat)

    Args:
        sql: Read-only SQL statement to execute. Can include database prefix
             (e.g., "SELECT * FROM beer_reviews.beer_reviews_flat" or
             "SELECT * FROM mysql.slow_log")
        max_rows: Maximum number of rows to return (default: 1000)
        timeout_seconds: Query timeout in seconds (default: 5)
        database: Optional database name to use. If not provided, will be extracted
                  from SQL if it contains database.table syntax, otherwise uses
                  default database from configuration.

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
def read_slow_log_file(
    path: str | None = None,
    max_bytes: int = 1_000_000,
    tail_lines: int = 5000,
) -> dict[str, Any]:
    """
    Read the tail of the MariaDB slow query log FILE.

    Use this only when log_output includes 'FILE' and table-based logs
    are unavailable. Returns raw text from the log tail.

    Args:
        path: Absolute path to the slow query log file. If omitted, the agent
              should first query SHOW VARIABLES LIKE 'slow_query_log_file';
              then pass that path into this tool.
        max_bytes: Maximum number of bytes to read from the end of the file (default: 1_000_000)
        tail_lines: Approximate number of lines from the end of the file (default: 5000)

    Returns:
        Dictionary with 'content' key containing the log file content
    """
    content = tail_slow_log_file(
        path=path,
        max_bytes=max_bytes,
        tail_lines=tail_lines,
    )
    return {"content": content}

