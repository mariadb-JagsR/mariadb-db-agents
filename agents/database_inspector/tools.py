# agents/database_inspector/tools.py
"""Tools for database inspection and SQL query execution."""

from __future__ import annotations

import logging
from typing import Any
from agents import function_tool
from ...common.db_client import run_readonly_query

logger = logging.getLogger(__name__)


@function_tool
def execute_sql(
    sql: str,
    max_rows: int = 100,
    timeout_seconds: int = 10,
    database: str | None = None,
) -> dict[str, Any]:
    """
    Execute a read-only SQL query against the database.
    
    Use this to:
    - Query information_schema tables (processlist, tables, columns, etc.)
    - Check GLOBAL_STATUS and GLOBAL_VARIABLES
    - Query performance_schema tables (if available)
    - Execute SHOW commands (SHOW STATUS, SHOW VARIABLES, SHOW PROCESSLIST, etc.)
    - Investigate specific tables or metrics
    - Follow up on recommendations from other agents
    
    Database connection is configured via environment variables (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_DATABASE).
    
    Args:
        sql: Read-only SQL statement (SELECT, SHOW, DESCRIBE, EXPLAIN)
        max_rows: Maximum number of rows to return (default: 100)
        timeout_seconds: Query timeout in seconds (default: 10)
        database: Optional database name to use
    
    Returns:
        Dictionary with:
        - 'rows': Query results (list of dictionaries)
        - 'row_count': Number of rows returned
        - 'columns': Column names (if available)
        - 'note': Additional information or warnings
    """
    try:
        rows = run_readonly_query(
            sql=sql,
            max_rows=max_rows,
            timeout_seconds=timeout_seconds,
            database=database,
        )
        
        # Extract column names from first row if available
        columns = list(rows[0].keys()) if rows else []
        
        note = ""
        if len(rows) >= max_rows:
            note = f"Result set limited to {max_rows} rows. There may be more results available."
        
        return {
            "rows": rows,
            "row_count": len(rows),
            "columns": columns,
            "note": note,
        }
    except Exception as e:
        logger.error(f"Error executing SQL query: {e}")
        return {
            "rows": [],
            "row_count": 0,
            "columns": [],
            "note": f"Error executing query: {str(e)}",
        }

