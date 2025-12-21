# agents/running_query/tools.py
from __future__ import annotations

from typing import Any
from agents import function_tool
from ...common.db_client import run_readonly_query


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
    - Query information_schema.processlist for running queries
    - Query information_schema.innodb_locks for lock information
    - Run EXPLAIN FORMAT=JSON on queries
    - Inspect schema/index metadata
    - Query any database tables

    Args:
        sql: Read-only SQL statement to execute
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
def get_processlist(
    include_sleeping: bool = False,
    min_time_seconds: float = 0.0,
    max_rows: int = 100,
) -> dict[str, Any]:
    """
    Get the current process list (running queries) from information_schema.processlist.

    This is the primary tool for analyzing currently executing SQL queries.
    It queries information_schema.processlist to get real-time information about
    active database connections and their queries.

    Args:
        include_sleeping: If True, include queries in 'Sleep' state (default: False)
        min_time_seconds: Minimum query execution time in seconds to include (default: 0.0)
        max_rows: Maximum number of processes to return (default: 100)

    Returns:
        Dictionary with 'rows' key containing process list entries with columns:
        - ID: Connection/thread ID
        - USER: Database user
        - HOST: Client host
        - DB: Database name
        - COMMAND: Command type (Query, Sleep, etc.)
        - TIME: Execution time in seconds
        - STATE: Query state (Locked, Waiting, etc.)
        - INFO: The SQL query text (if available)
    """
    # Build the query
    conditions = []
    if not include_sleeping:
        conditions.append("COMMAND != 'Sleep'")
    if min_time_seconds > 0:
        conditions.append(f"TIME >= {min_time_seconds}")

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    sql = f"""
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
        {where_clause}
        ORDER BY TIME DESC
        LIMIT {max_rows}
    """

    rows = run_readonly_query(
        sql=sql,
        max_rows=max_rows,
        timeout_seconds=5,
        database=None,  # information_schema doesn't need a specific database
    )
    return {"rows": rows}

