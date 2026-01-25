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

  # Check replication health
  mariadb-db-agents replication-health

  # Execute SQL queries (Database Inspector)
  mariadb-db-agents inspector "SELECT * FROM information_schema.tables LIMIT 10"
  mariadb-db-agents inspector "What tables are in the database?"

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
        "--slow-log-path",
        type=str,
        default=None,
        help="Path to slow query log file (for local file access). If provided, will read from this file instead of mysql.slow_log table.",
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

    # Replication Health Agent
    replication_parser = subparsers.add_parser(
        "replication-health",
        help="Check replication health: monitor lag, detect failures, analyze replication status",
        description="Replication Health Agent: Monitors replication lag across all replicas, detects failures, "
                    "and provides recommendations. Database connection is configured via environment variables "
                    "(DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_DATABASE).",
    )
    replication_parser.add_argument(
        "--max-executions",
        type=int,
        default=10,
        help="Number of times to execute SHOW ALL SLAVES STATUS to discover replicas (default: 10). "
             "SkySQL has a maximum of 5 replicas, so 10 executions ensures coverage.",
    )
    replication_parser.add_argument(
        "--max-turns",
        type=int,
        default=30,
        help="Maximum number of agent turns/tool calls (default: 30). Increase if agent needs more steps.",
    )

    # Database Inspector Agent
    inspector_parser = subparsers.add_parser(
        "inspector",
        help="Database Inspector: Execute read-only SQL queries and explore database",
        description="Database Inspector Agent: Execute read-only SQL queries, check status/variables, "
                    "explore schema, and investigate database state. "
                    "Database connection is configured via environment variables "
                    "(DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_DATABASE).",
    )
    inspector_parser.add_argument(
        "query",
        nargs="?",
        type=str,
        default=None,
        help="SQL query to execute or question about the database (e.g., 'SELECT * FROM information_schema.tables', 'What tables are in the database?')",
    )
    inspector_parser.add_argument(
        "--max-rows",
        type=int,
        default=100,
        help="Maximum number of rows to return (default: 100)",
    )
    inspector_parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Query timeout in seconds (default: 10)",
    )
    inspector_parser.add_argument(
        "--max-turns",
        type=int,
        default=10,
        help="Maximum number of agent turns/tool calls (default: 10)",
    )

    return parser


def main() -> int:
    """Main entry point for the unified CLI."""
    parser = create_parser()
    original_argv = sys.argv[1:]
    global_interactive = "--interactive" in original_argv
    cleaned_argv = [arg for arg in original_argv if arg != "--interactive"]

    # Detect subcommands so we can auto-insert 'orchestrator' for bare queries.
    subparsers_action = next(
        (action for action in parser._actions if isinstance(action, argparse._SubParsersAction)),
        None,
    )
    known_agents = set()
    if subparsers_action is not None:
        known_agents = set(subparsers_action._name_parser_map.keys())

    agent_in_argv = any(token in known_agents for token in cleaned_argv)
    has_positional = any(not token.startswith("-") for token in cleaned_argv)
    inserted_orchestrator = False
    if not agent_in_argv and has_positional:
        cleaned_argv.insert(0, "orchestrator")
        inserted_orchestrator = True

    args = parser.parse_args(cleaned_argv)

    # Apply the global --interactive flag (if provided before subcommand).
    if global_interactive and not hasattr(args, "interactive"):
        parser.error("unrecognized arguments: --interactive")
    if global_interactive and hasattr(args, "interactive"):
        args.interactive = True

    # If we auto-inserted orchestrator for a bare query, default to one-shot unless
    # the user explicitly requested interactive mode.
    if inserted_orchestrator and hasattr(args, "interactive"):
        args.interactive = True if global_interactive else False

    if not args.agent:
        parser.print_help()
        return 1

    # Route to appropriate agent
    if args.agent == "slow-query":
        if args.interactive:
            # Import and run conversation mode
            import asyncio
            from mariadb_db_agents.agents.slow_query.conversation import main as conversation_main
            return asyncio.run(conversation_main())
        else:
            # Import and run CLI mode
            from mariadb_db_agents.agents.slow_query.main import main as agent_main
            # Convert args to list for agent_main
            agent_args = [
                "--hours", str(args.hours),
                "--max-patterns", str(args.max_patterns),
            ]
            if hasattr(args, 'slow_log_path') and args.slow_log_path:
                agent_args.extend(["--slow-log-path", args.slow_log_path])
            return agent_main(agent_args)

    elif args.agent == "running-query":
        if args.interactive:
            # Import and run conversation mode
            import asyncio
            from mariadb_db_agents.agents.running_query.conversation import main as conversation_main
            return asyncio.run(conversation_main())
        else:
            # Import and run CLI mode
            from mariadb_db_agents.agents.running_query.main import main as agent_main
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
        from mariadb_db_agents.agents.incident_triage.main import main as agent_main
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
            # Import and run conversation mode; pass positional query as initial
            # message if present so it becomes the first conversation item.
            import asyncio
            from mariadb_db_agents.orchestrator.conversation import main as conversation_main
            initial_query = args.query if hasattr(args, "query") else None
            return asyncio.run(conversation_main(initial_query))
        else:
            # Import and run CLI mode
            from mariadb_db_agents.orchestrator.main import main as orchestrator_main
            # Convert args to list for orchestrator_main
            orchestrator_args = [
                "--max-turns", str(args.max_turns),
            ]
            # Handle query - if provided as positional arg, use it; otherwise it's None
            # The orchestrator will prompt interactively if query is None
            if hasattr(args, 'query') and args.query:
                orchestrator_args.append(args.query)
            return orchestrator_main(orchestrator_args)

    elif args.agent == "replication-health":
        # Import and run replication health agent
        from mariadb_db_agents.agents.replication_health.main import main as replication_main
        # Convert args to list for replication_main
        replication_args = [
            "--max-executions", str(args.max_executions),
            "--max-turns", str(args.max_turns),
        ]
        return replication_main(replication_args)

    elif args.agent == "inspector":
        # Import and run database inspector agent
        from mariadb_db_agents.agents.database_inspector.main import main as inspector_main
        # Convert args to list for inspector_main
        inspector_args = [
            "--max-rows", str(args.max_rows),
            "--timeout", str(args.timeout),
            "--max-turns", str(args.max_turns),
        ]
        if args.query:
            inspector_args.append(args.query)
        return inspector_main(inspector_args)

    else:
        print(f"Unknown agent: {args.agent}", file=sys.stderr)
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())

