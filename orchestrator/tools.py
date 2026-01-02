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
    from ..common.observability import get_tracker, add_orchestrator_sub_agent_metric
    
    try:
        # Track metrics before running agent
        tracker = get_tracker()
        interactions_before = len(tracker.interactions)
        
        result = await run_agent_async(
            time_window_hours=hours,
            max_patterns=max_patterns,
        )
        
        # Capture sub-agent metrics
        interactions_after = len(tracker.interactions)
        if interactions_after > interactions_before:
            # Get the last interaction (the sub-agent's metrics)
            sub_agent_metrics = tracker.interactions[-1]
            add_orchestrator_sub_agent_metric("slow_query", {
                "llm_round_trips": sub_agent_metrics.llm_round_trips,
                "total_input_tokens": sub_agent_metrics.total_input_tokens,
                "total_output_tokens": sub_agent_metrics.total_output_tokens,
                "total_tokens": sub_agent_metrics.total_tokens,
                "cached_tokens": sub_agent_metrics.cached_tokens,
                "reasoning_tokens": sub_agent_metrics.reasoning_tokens,
            })
        
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
    from ..common.observability import get_tracker, add_orchestrator_sub_agent_metric
    
    try:
        # Track metrics before running agent
        tracker = get_tracker()
        interactions_before = len(tracker.interactions)
        
        result = await run_agent_async(
            min_time_seconds=min_time_seconds,
            include_sleeping=include_sleeping,
            max_queries=max_queries,
        )
        
        # Capture sub-agent metrics
        interactions_after = len(tracker.interactions)
        if interactions_after > interactions_before:
            # Get the last interaction (the sub-agent's metrics)
            sub_agent_metrics = tracker.interactions[-1]
            add_orchestrator_sub_agent_metric("running_query", {
                "llm_round_trips": sub_agent_metrics.llm_round_trips,
                "total_input_tokens": sub_agent_metrics.total_input_tokens,
                "total_output_tokens": sub_agent_metrics.total_output_tokens,
                "total_tokens": sub_agent_metrics.total_tokens,
                "cached_tokens": sub_agent_metrics.cached_tokens,
                "reasoning_tokens": sub_agent_metrics.reasoning_tokens,
            })
        
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
    from ..common.observability import get_tracker, add_orchestrator_sub_agent_metric
    
    try:
        # Track metrics before running agent
        tracker = get_tracker()
        interactions_before = len(tracker.interactions)
        
        result = await run_agent_async(
            error_log_path=error_log_path,
            service_id=service_id,
            max_error_patterns=max_error_patterns,
            error_log_lines=error_log_lines,
            max_turns=max_turns,
        )
        
        # Capture sub-agent metrics
        interactions_after = len(tracker.interactions)
        if interactions_after > interactions_before:
            # Get the last interaction (the sub-agent's metrics)
            sub_agent_metrics = tracker.interactions[-1]
            add_orchestrator_sub_agent_metric("incident_triage", {
                "llm_round_trips": sub_agent_metrics.llm_round_trips,
                "total_input_tokens": sub_agent_metrics.total_input_tokens,
                "total_output_tokens": sub_agent_metrics.total_output_tokens,
                "total_tokens": sub_agent_metrics.total_tokens,
                "cached_tokens": sub_agent_metrics.cached_tokens,
                "reasoning_tokens": sub_agent_metrics.reasoning_tokens,
            })
        
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


@function_tool
async def check_replication_health(
    max_executions: int = 10,
    max_turns: int = 30,
) -> dict[str, Any]:
    """
    Invoke Replication Health Agent to monitor replication lag and health across all replicas.
    
    Use this when the user asks about:
    - Replication health, replication lag, replication status
    - "Why is replication lagging?"
    - "Check replication health"
    - "Is replication working?"
    - Replication failures, replication errors
    
    This agent monitors all replicas, detects lag, identifies failures, and provides recommendations.
    
    Args:
        max_executions: Number of times to execute SHOW ALL SLAVES STATUS to discover replicas (default: 10)
        max_turns: Maximum number of agent turns/tool calls (default: 30)
    
    Returns:
        Dictionary with 'report' (agent output) and 'agent' (agent name)
    """
    from ..agents.replication_health.main import run_agent_async
    from ..common.observability import get_tracker, add_orchestrator_sub_agent_metric
    
    try:
        # Track metrics before running agent
        tracker = get_tracker()
        interactions_before = len(tracker.interactions)
        
        result = await run_agent_async(
            max_executions=max_executions,
            max_turns=max_turns,
        )
        
        # Capture sub-agent metrics
        interactions_after = len(tracker.interactions)
        if interactions_after > interactions_before:
            # Get the last interaction (the sub-agent's metrics)
            sub_agent_metrics = tracker.interactions[-1]
            add_orchestrator_sub_agent_metric("replication_health", {
                "llm_round_trips": sub_agent_metrics.llm_round_trips,
                "total_input_tokens": sub_agent_metrics.total_input_tokens,
                "total_output_tokens": sub_agent_metrics.total_output_tokens,
                "total_tokens": sub_agent_metrics.total_tokens,
                "cached_tokens": sub_agent_metrics.cached_tokens,
                "reasoning_tokens": sub_agent_metrics.reasoning_tokens,
            })
        
        return {
            "report": result,
            "agent": "replication_health",
            "success": True,
        }
    except Exception as e:
        return {
            "report": f"Error running Replication Health Agent: {str(e)}",
            "agent": "replication_health",
            "success": False,
            "error": str(e),
        }


@function_tool
async def execute_database_query(
    sql: str,
    max_rows: int = 100,
    timeout_seconds: int = 10,
) -> dict[str, Any]:
    """
    Execute a read-only SQL query using the Database Inspector Agent.
    
    Use this to execute SQL queries recommended by other agents or requested by users.
    Supports SELECT, SHOW, DESCRIBE, EXPLAIN statements on information_schema,
    performance_schema, GLOBAL_STATUS, GLOBAL_VARIABLES, and user tables.
    
    Args:
        sql: Read-only SQL statement to execute
        max_rows: Maximum rows to return (default: 100)
        timeout_seconds: Query timeout (default: 10)
    
    Returns:
        Dictionary with 'report' (query results) and 'agent' (agent name)
    """
    from ..agents.database_inspector.main import run_agent_async
    from ..common.observability import get_tracker, add_orchestrator_sub_agent_metric
    
    try:
        # Track metrics before running agent
        tracker = get_tracker()
        interactions_before = len(tracker.interactions)
        
        result = await run_agent_async(
            query=sql,
            max_rows=max_rows,
            timeout=timeout_seconds,
            max_turns=5,  # Inspector agent typically needs few turns
        )
        
        # Capture sub-agent metrics
        interactions_after = len(tracker.interactions)
        if interactions_after > interactions_before:
            # Get the last interaction (the sub-agent's metrics)
            sub_agent_metrics = tracker.interactions[-1]
            add_orchestrator_sub_agent_metric("database_inspector", {
                "llm_round_trips": sub_agent_metrics.llm_round_trips,
                "total_input_tokens": sub_agent_metrics.total_input_tokens,
                "total_output_tokens": sub_agent_metrics.total_output_tokens,
                "total_tokens": sub_agent_metrics.total_tokens,
                "cached_tokens": sub_agent_metrics.cached_tokens,
                "reasoning_tokens": sub_agent_metrics.reasoning_tokens,
            })
        
        return {
            "report": result,
            "agent": "database_inspector",
            "success": True,
        }
    except Exception as e:
        return {
            "report": f"Error executing database query: {str(e)}",
            "agent": "database_inspector",
            "success": False,
            "error": str(e),
        }

