# mcp_server/main.py
"""MCP Server entry point for MariaDB Database Management Agents."""

from __future__ import annotations

import asyncio
import logging
import sys
from typing import Any

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:
    print(
        "Error: MCP SDK not installed. Please install it with:\n"
        "  pip install mcp>=0.9.0\n"
        "Or install all dependencies:\n"
        "  pip install -r requirements.txt",
        file=sys.stderr,
    )
    sys.exit(1)

from .tools import (
    orchestrator_query,
    analyze_slow_queries,
    analyze_running_queries,
    perform_incident_triage,
    check_replication_health,
    execute_database_query,
)

# Configure logging
logging.basicConfig(
    level=logging.WARNING,  # Reduce noise from MCP SDK
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create MCP server
server = Server("mariadb-db-agents")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools."""
    return [
        Tool(
            name="orchestrator_query",
            description=(
                "Query the DBA Orchestrator agent with a natural language question. "
                "The orchestrator intelligently routes your query to appropriate specialized agents "
                "and synthesizes comprehensive reports. This is the recommended entry point for "
                "most database management tasks. Examples: 'Is my database healthy?', "
                "'Analyze slow queries from the last hour', 'What queries are running right now?'"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language query about database management",
                    },
                    "max_turns": {
                        "type": "integer",
                        "description": "Maximum number of agent turns/tool calls (default: 30)",
                        "default": 30,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="analyze_slow_queries",
            description=(
                "Analyze historical slow queries from slow query logs. "
                "Identifies patterns and provides optimization recommendations."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "hours": {
                        "type": "number",
                        "description": "Time window in hours to analyze slow queries (default: 1.0)",
                        "default": 1.0,
                    },
                    "max_patterns": {
                        "type": "integer",
                        "description": "Maximum number of query patterns to analyze in detail (default: 8)",
                        "default": 8,
                    },
                    "slow_log_path": {
                        "type": "string",
                        "description": "Optional path to slow query log file (for local file access)",
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="analyze_running_queries",
            description=(
                "Analyze currently executing SQL queries in real-time. "
                "Identifies long-running queries, blocking queries, and provides immediate troubleshooting recommendations."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "min_time_seconds": {
                        "type": "number",
                        "description": "Minimum query execution time in seconds to analyze (default: 1.0)",
                        "default": 1.0,
                    },
                    "include_sleeping": {
                        "type": "boolean",
                        "description": "Whether to include sleeping/idle connections (default: False)",
                        "default": False,
                    },
                    "max_queries": {
                        "type": "integer",
                        "description": "Maximum number of queries to analyze in detail (default: 20)",
                        "default": 20,
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="perform_incident_triage",
            description=(
                "Perform a quick health check and identify database issues. "
                "Provides actionable checklists for troubleshooting. Ideal for 'something's wrong' scenarios."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "error_log_path": {
                        "type": "string",
                        "description": "Path to error log file (for local file access)",
                    },
                    "service_id": {
                        "type": "string",
                        "description": "SkySQL service ID for API-based error log access",
                    },
                    "max_error_patterns": {
                        "type": "integer",
                        "description": "Maximum number of error patterns to extract (default: 20)",
                        "default": 20,
                    },
                    "error_log_lines": {
                        "type": "integer",
                        "description": "Number of lines to read from error log tail (default: 5000)",
                        "default": 5000,
                    },
                    "max_turns": {
                        "type": "integer",
                        "description": "Maximum number of agent turns/tool calls (default: 30)",
                        "default": 30,
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="check_replication_health",
            description=(
                "Monitor replication lag and health across all replicas. "
                "Detects lag, identifies failures, and provides recommendations for replication optimization."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "max_executions": {
                        "type": "integer",
                        "description": "Number of times to execute SHOW ALL SLAVES STATUS to discover replicas (default: 10)",
                        "default": 10,
                    },
                    "max_turns": {
                        "type": "integer",
                        "description": "Maximum number of agent turns/tool calls (default: 30)",
                        "default": 30,
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="execute_database_query",
            description=(
                "Execute a read-only SQL query for database investigation. "
                "Supports SELECT, SHOW, DESCRIBE, EXPLAIN statements. "
                "Useful for follow-up analysis after other agents provide recommendations."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "SQL query to execute or question about the database",
                    },
                    "max_rows": {
                        "type": "integer",
                        "description": "Maximum number of rows to return (default: 100)",
                        "default": 100,
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Query timeout in seconds (default: 10)",
                        "default": 10,
                    },
                    "max_turns": {
                        "type": "integer",
                        "description": "Maximum number of agent turns/tool calls (default: 10)",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    try:
        if name == "orchestrator_query":
            result = await orchestrator_query(
                query=arguments["query"],
                max_turns=arguments.get("max_turns", 30),
            )
        elif name == "analyze_slow_queries":
            result = await analyze_slow_queries(
                hours=arguments.get("hours", 1.0),
                max_patterns=arguments.get("max_patterns", 8),
                slow_log_path=arguments.get("slow_log_path"),
            )
        elif name == "analyze_running_queries":
            result = await analyze_running_queries(
                min_time_seconds=arguments.get("min_time_seconds", 1.0),
                include_sleeping=arguments.get("include_sleeping", False),
                max_queries=arguments.get("max_queries", 20),
            )
        elif name == "perform_incident_triage":
            result = await perform_incident_triage(
                error_log_path=arguments.get("error_log_path"),
                service_id=arguments.get("service_id"),
                max_error_patterns=arguments.get("max_error_patterns", 20),
                error_log_lines=arguments.get("error_log_lines", 5000),
                max_turns=arguments.get("max_turns", 30),
            )
        elif name == "check_replication_health":
            result = await check_replication_health(
                max_executions=arguments.get("max_executions", 10),
                max_turns=arguments.get("max_turns", 30),
            )
        elif name == "execute_database_query":
            result = await execute_database_query(
                query=arguments["query"],
                max_rows=arguments.get("max_rows", 100),
                timeout=arguments.get("timeout", 10),
                max_turns=arguments.get("max_turns", 10),
            )
        else:
            result = f"Unknown tool: {name}"
        
        return [TextContent(type="text", text=str(result))]
    except Exception as e:
        error_msg = f"Error executing tool {name}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return [TextContent(type="text", text=error_msg)]


async def main() -> None:
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        init_options = server.create_initialization_options()
        await server.run(
            read_stream,
            write_stream,
            init_options,
        )


if __name__ == "__main__":
    asyncio.run(main())

