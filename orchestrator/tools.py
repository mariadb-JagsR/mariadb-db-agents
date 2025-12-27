# orchestrator/tools.py
"""Tools for invoking specialized agents from the orchestrator."""

from __future__ import annotations

import asyncio
from typing import Any
from agents import function_tool


@function_tool
async def analyze_slow_queries(
    hours: float = 1.0,
    max_patterns: int = 8,
) -> dict[str, Any]:
    """
    Invoke Slow Query Agent to analyze historical slow queries from slow query logs.
    
    Use this when the user asks about:
    - Slow queries, query performance, query optimization
    - Historical query patterns
    - Query tuning opportunities
    
    Args:
        hours: Time window in hours to analyze slow queries (default: 1.0)
        max_patterns: Maximum number of query patterns to analyze in detail (default: 8)
    
    Returns:
        Dictionary with 'report' (agent output) and 'agent' (agent name)
    """
    from ..agents.slow_query.main import run_agent_async
    
    try:
        result = await run_agent_async(
            time_window_hours=hours,
            max_patterns=max_patterns,
        )
        return {
            "report": result,
            "agent": "slow_query",
            "success": True,
        }
    except Exception as e:
        return {
            "report": f"Error running Slow Query Agent: {str(e)}",
            "agent": "slow_query",
            "success": False,
            "error": str(e),
        }


@function_tool
async def analyze_running_queries(
    min_time_seconds: float = 1.0,
    include_sleeping: bool = False,
    max_queries: int = 20,
) -> dict[str, Any]:
    """
    Invoke Running Query Agent to analyze currently executing SQL queries in real-time.
    
    Use this when the user asks about:
    - Running queries, current queries, active queries
    - Blocking queries, long-running queries
    - What's happening right now in the database
    
    Args:
        min_time_seconds: Minimum query execution time in seconds to analyze (default: 1.0)
        include_sleeping: Whether to include sleeping/idle connections (default: False)
        max_queries: Maximum number of queries to analyze in detail (default: 20)
    
    Returns:
        Dictionary with 'report' (agent output) and 'agent' (agent name)
    """
    from ..agents.running_query.main import run_agent_async
    
    try:
        result = await run_agent_async(
            min_time_seconds=min_time_seconds,
            include_sleeping=include_sleeping,
            max_queries=max_queries,
        )
        return {
            "report": result,
            "agent": "running_query",
            "success": True,
        }
    except Exception as e:
        return {
            "report": f"Error running Running Query Agent: {str(e)}",
            "agent": "running_query",
            "success": False,
            "error": str(e),
        }


@function_tool
async def perform_incident_triage(
    error_log_path: str | None = None,
    service_id: str | None = None,
    max_error_patterns: int = 20,
    error_log_lines: int = 5000,
    max_turns: int = 30,
) -> dict[str, Any]:
    """
    Invoke Incident Triage Agent to quickly identify database issues and provide actionable checklists.
    
    Use this when the user asks about:
    - Health checks, database health, "is everything ok"
    - "Something's wrong", incidents, troubleshooting
    - Quick status checks, "what's the problem"
    
    This agent performs a quick health snapshot and identifies top issues.
    It's often a good starting point before diving into specific agents.
    
    Args:
        error_log_path: Path to error log file (for local file access)
        service_id: SkySQL service ID for API-based error log access
        max_error_patterns: Maximum number of error patterns to extract (default: 20)
        error_log_lines: Number of lines to read from error log tail (default: 5000)
        max_turns: Maximum number of agent turns/tool calls (default: 30)
    
    Returns:
        Dictionary with 'report' (agent output) and 'agent' (agent name)
    """
    from ..agents.incident_triage.main import run_agent_async
    
    try:
        result = await run_agent_async(
            error_log_path=error_log_path,
            service_id=service_id,
            max_error_patterns=max_error_patterns,
            error_log_lines=error_log_lines,
            max_turns=max_turns,
        )
        return {
            "report": result,
            "agent": "incident_triage",
            "success": True,
        }
    except Exception as e:
        return {
            "report": f"Error running Incident Triage Agent: {str(e)}",
            "agent": "incident_triage",
            "success": False,
            "error": str(e),
        }

