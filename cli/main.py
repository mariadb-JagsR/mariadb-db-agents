#!/usr/bin/env python3
"""
Unified CLI entry point for MariaDB Database Management Agents.

This provides a single command-line interface to access all specialized agents.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any


def create_parser() -> argparse.ArgumentParser:
    """Create the main argument parser."""
    parser = argparse.ArgumentParser(
        prog="mariadb-db-agents",
        description="MariaDB Database Management Agents - AI-powered database analysis and optimization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze slow queries
  mariadb-db-agents slow-query --hours 1

  # Analyze running queries
  mariadb-db-agents running-query --min-time-seconds 5

  # Perform incident triage
  mariadb-db-agents incident-triage --error-log-path /var/log/mysql/error.log

  # Use orchestrator (intelligent routing to specialized agents)
  mariadb-db-agents orchestrator "Is my database healthy?"
  mariadb-db-agents orchestrator "Analyze slow queries from the last hour"
  mariadb-db-agents orchestrator --interactive

  # Interactive conversation mode
  mariadb-db-agents slow-query --interactive
  mariadb-db-agents running-query --interactive
  mariadb-db-agents orchestrator --interactive

For more information about a specific agent, use:
  mariadb-db-agents <agent> --help
        """,
    )

    subparsers = parser.add_subparsers(
        dest="agent",
        help="Agent to run",
        metavar="AGENT",
    )

    # Slow Query Agent
    slow_query_parser = subparsers.add_parser(
        "slow-query",
        help="Analyze historical slow queries from slow query logs",
        description="Slow Query Agent: Analyzes historical slow queries and provides optimization recommendations. "
                    "Database connection is configured via environment variables (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_DATABASE).",
    )
    slow_query_parser.add_argument(
        "--hours",
        type=float,
        default=1.0,
        help="Approximate time window in hours to analyze slow queries (default: 1.0).",
    )
    slow_query_parser.add_argument(
        "--max-patterns",
        type=int,
        default=8,
        help="Maximum number of query patterns to deep-analyze (default: 8).",
    )
    slow_query_parser.add_argument(
        "--interactive",
        action="store_true",
        help="Start interactive conversation mode instead of one-time analysis.",
    )

    # Running Query Agent
    running_query_parser = subparsers.add_parser(
        "running-query",
        help="Analyze currently executing SQL queries in real-time",
        description="Running Query Agent: Analyzes currently executing queries and identifies problematic queries. "
                    "Database connection is configured via environment variables (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_DATABASE).",
    )
    running_query_parser.add_argument(
        "--min-time-seconds",
        type=float,
        default=1.0,
        help="Minimum query execution time in seconds to analyze (default: 1.0).",
    )
    running_query_parser.add_argument(
        "--include-sleeping",
        action="store_true",
        help="Include sleeping/idle connections in the analysis.",
    )
    running_query_parser.add_argument(
        "--max-queries",
        type=int,
        default=20,
        help="Maximum number of queries to analyze in detail (default: 20).",
    )
    running_query_parser.add_argument(
        "--interactive",
        action="store_true",
        help="Start interactive conversation mode instead of one-time analysis.",
    )

    # Incident Triage Agent
    incident_triage_parser = subparsers.add_parser(
        "incident-triage",
        help="Perform incident triage: identify what's wrong and where to look first",
        description="Incident Triage Agent: Quickly identifies database issues and provides prioritized checklist. "
                    "Database connection is configured via environment variables (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_DATABASE).",
    )
    incident_triage_parser.add_argument(
        "--error-log-path",
        type=str,
        default=None,
        help="Path to error log file (for local file access). If not provided, will attempt SkySQL API if service_id is set.",
    )
    incident_triage_parser.add_argument(
        "--service-id",
        type=str,
        default=None,
        help="SkySQL service ID for API-based error log access (if not using local file).",
    )
    incident_triage_parser.add_argument(
        "--max-error-patterns",
        type=int,
        default=20,
        help="Maximum number of error patterns to extract from error log (default: 20).",
    )
    incident_triage_parser.add_argument(
        "--error-log-lines",
        type=int,
        default=5000,
        help="Number of lines to read from error log tail (default: 5000).",
    )
    incident_triage_parser.add_argument(
        "--max-turns",
        type=int,
        default=30,
        help="Maximum number of agent turns/tool calls (default: 30). Increase if agent needs more steps to complete analysis.",
    )

    # Orchestrator Agent
    orchestrator_parser = subparsers.add_parser(
        "orchestrator",
        help="DBA Orchestrator: Intelligently routes queries to specialized agents",
        description="Orchestrator Agent: A meta-agent that routes user queries to appropriate specialized agents "
                    "and synthesizes comprehensive reports. "
                    "Database connection is configured via environment variables (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_DATABASE).",
    )
    orchestrator_parser.add_argument(
        "query",
        nargs="?",
        type=str,
        default=None,
        help="User query about database management (e.g., 'Is my database healthy?', 'Analyze slow queries'). "
             "If not provided, will prompt interactively (unless --interactive is used).",
    )
    orchestrator_parser.add_argument(
        "--max-turns",
        type=int,
        default=30,
        help="Maximum number of agent turns/tool calls (default: 30). Increase if orchestrator needs more steps.",
    )
    orchestrator_parser.add_argument(
        "--interactive",
        action="store_true",
        help="Start interactive conversation mode instead of one-time analysis.",
    )

    return parser


def main() -> int:
    """Main entry point for the unified CLI."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.agent:
        parser.print_help()
        return 1

    # Route to appropriate agent
    if args.agent == "slow-query":
        if args.interactive:
            # Import and run conversation mode
            import asyncio
            from ..agents.slow_query.conversation import main as conversation_main
            return asyncio.run(conversation_main())
        else:
            # Import and run CLI mode
            from ..agents.slow_query.main import main as agent_main
            # Convert args to list for agent_main
            agent_args = [
                "--hours", str(args.hours),
                "--max-patterns", str(args.max_patterns),
            ]
            return agent_main(agent_args)

    elif args.agent == "running-query":
        if args.interactive:
            # Import and run conversation mode
            import asyncio
            from ..agents.running_query.conversation import main as conversation_main
            return asyncio.run(conversation_main())
        else:
            # Import and run CLI mode
            from ..agents.running_query.main import main as agent_main
            # Convert args to list for agent_main
            agent_args = [
                "--min-time-seconds", str(args.min_time_seconds),
                "--max-queries", str(args.max_queries),
            ]
            if args.include_sleeping:
                agent_args.append("--include-sleeping")
            return agent_main(agent_args)

    elif args.agent == "incident-triage":
        # Import and run CLI mode
        from ..agents.incident_triage.main import main as agent_main
        # Convert args to list for agent_main
        agent_args = [
            "--max-error-patterns", str(args.max_error_patterns),
            "--error-log-lines", str(args.error_log_lines),
            "--max-turns", str(args.max_turns),
        ]
        if args.error_log_path:
            agent_args.extend(["--error-log-path", args.error_log_path])
        if args.service_id:
            agent_args.extend(["--service-id", args.service_id])
        return agent_main(agent_args)

    elif args.agent == "orchestrator":
        if args.interactive:
            # Import and run conversation mode
            import asyncio
            from ..orchestrator.conversation import main as conversation_main
            return asyncio.run(conversation_main())
        else:
            # Import and run CLI mode
            from ..orchestrator.main import main as orchestrator_main
            # Convert args to list for orchestrator_main
            orchestrator_args = [
                "--max-turns", str(args.max_turns),
            ]
            # Handle query - if provided as positional arg, use it; otherwise it's None
            # The orchestrator will prompt interactively if query is None
            if hasattr(args, 'query') and args.query:
                orchestrator_args.append(args.query)
            return orchestrator_main(orchestrator_args)

    else:
        print(f"Unknown agent: {args.agent}", file=sys.stderr)
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())

