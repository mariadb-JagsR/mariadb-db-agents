# mcp_server/tools.py
"""MCP tool implementations for MariaDB database management agents."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def orchestrator_query(
    query: str,
    max_turns: int = 30,
) -> str:
    """
    Query the DBA Orchestrator agent with a natural language question.
    
    The orchestrator intelligently routes your query to appropriate specialized agents
    and synthesizes comprehensive reports. This is the recommended entry point for
    most database management tasks.
    
    Args:
        query: Natural language query about database management (e.g., "Is my database healthy?",
              "Analyze slow queries from the last hour", "What queries are running right now?")
        max_turns: Maximum number of agent turns/tool calls (default: 30)
    
    Returns:
        Comprehensive report from the orchestrator
    """
    try:
        from ..orchestrator.main import run_orchestrator_async
        
        logger.info(f"Running orchestrator query: {query}")
        result = await run_orchestrator_async(
            user_query=query,
            max_turns=max_turns,
        )
        return result
    except Exception as e:
        error_msg = f"Error running orchestrator: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg


async def analyze_slow_queries(
    hours: float = 1.0,
    max_patterns: int = 8,
    slow_log_path: str | None = None,
) -> str:
    """
    Analyze historical slow queries from slow query logs.
    
    This agent analyzes slow queries from the mysql.slow_log table or a local log file,
    identifies patterns, and provides optimization recommendations.
    
    Args:
        hours: Time window in hours to analyze slow queries (default: 1.0)
        max_patterns: Maximum number of query patterns to analyze in detail (default: 8)
        slow_log_path: Optional path to slow query log file (for local file access)
    
    Returns:
        Analysis report with query patterns and optimization recommendations
    """
    try:
        from ..agents.slow_query.main import run_agent_async
        
        logger.info(f"Running slow query analysis: hours={hours}, max_patterns={max_patterns}")
        result = await run_agent_async(
            time_window_hours=hours,
            max_patterns=max_patterns,
            slow_log_path=slow_log_path,
        )
        return result
    except Exception as e:
        error_msg = f"Error running slow query agent: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg


async def analyze_running_queries(
    min_time_seconds: float = 1.0,
    include_sleeping: bool = False,
    max_queries: int = 20,
) -> str:
    """
    Analyze currently executing SQL queries in real-time.
    
    This agent identifies long-running queries, blocking queries, and queries
    in problematic states, providing immediate troubleshooting recommendations.
    
    Args:
        min_time_seconds: Minimum query execution time in seconds to analyze (default: 1.0)
        include_sleeping: Whether to include sleeping/idle connections (default: False)
        max_queries: Maximum number of queries to analyze in detail (default: 20)
    
    Returns:
        Analysis report with current query status and recommendations
    """
    try:
        from ..agents.running_query.main import run_agent_async
        
        logger.info(f"Running running query analysis: min_time_seconds={min_time_seconds}")
        result = await run_agent_async(
            min_time_seconds=min_time_seconds,
            include_sleeping=include_sleeping,
            max_queries=max_queries,
        )
        return result
    except Exception as e:
        error_msg = f"Error running running query agent: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg


async def perform_incident_triage(
    error_log_path: str | None = None,
    service_id: str | None = None,
    max_error_patterns: int = 20,
    error_log_lines: int = 5000,
    max_turns: int = 30,
) -> str:
    """
    Perform a quick health check and identify database issues.
    
    This agent performs a quick health snapshot, analyzes error logs, and provides
    actionable checklists for troubleshooting. It's ideal for "something's wrong" scenarios.
    
    Args:
        error_log_path: Path to error log file (for local file access)
        service_id: SkySQL service ID for API-based error log access
        max_error_patterns: Maximum number of error patterns to extract (default: 20)
        error_log_lines: Number of lines to read from error log tail (default: 5000)
        max_turns: Maximum number of agent turns/tool calls (default: 30)
    
    Returns:
        Health check report with identified issues and actionable recommendations
    """
    try:
        from ..agents.incident_triage.main import run_agent_async
        
        logger.info("Running incident triage")
        result = await run_agent_async(
            error_log_path=error_log_path,
            service_id=service_id,
            max_error_patterns=max_error_patterns,
            error_log_lines=error_log_lines,
            max_turns=max_turns,
        )
        return result
    except Exception as e:
        error_msg = f"Error running incident triage agent: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg


async def check_replication_health(
    max_executions: int = 10,
    max_turns: int = 30,
) -> str:
    """
    Monitor replication lag and health across all replicas.
    
    This agent monitors all replicas, detects lag, identifies failures, and provides
    recommendations for replication optimization.
    
    Args:
        max_executions: Number of times to execute SHOW ALL SLAVES STATUS to discover replicas (default: 10)
        max_turns: Maximum number of agent turns/tool calls (default: 30)
    
    Returns:
        Replication health report with lag analysis and recommendations
    """
    try:
        from ..agents.replication_health.main import run_agent_async
        
        logger.info("Running replication health check")
        result = await run_agent_async(
            max_executions=max_executions,
            max_turns=max_turns,
        )
        return result
    except Exception as e:
        error_msg = f"Error running replication health agent: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg


async def execute_database_query(
    query: str,
    max_rows: int = 100,
    timeout: int = 10,
    max_turns: int = 10,
) -> str:
    """
    Execute a read-only SQL query for database investigation.
    
    This agent executes read-only SQL queries (SELECT, SHOW, DESCRIBE, EXPLAIN) and
    provides formatted results with insights. Useful for follow-up analysis after
    other agents provide recommendations.
    
    Args:
        query: SQL query to execute or question about the database
        max_rows: Maximum number of rows to return (default: 100)
        timeout: Query timeout in seconds (default: 10)
        max_turns: Maximum number of agent turns/tool calls (default: 10)
    
    Returns:
        Query results with formatted output and insights
    """
    try:
        from ..agents.database_inspector.main import run_agent_async
        
        logger.info(f"Executing database query: {query[:100]}...")
        result = await run_agent_async(
            query=query,
            max_rows=max_rows,
            timeout=timeout,
            max_turns=max_turns,
        )
        return result
    except Exception as e:
        error_msg = f"Error executing database query: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg

