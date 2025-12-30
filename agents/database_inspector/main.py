# agents/database_inspector/main.py
"""CLI entry point for the Database Inspector Agent."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from agents import Runner, set_default_openai_key
from ...common.config import OpenAIConfig
from .agent import create_database_inspector_agent
from ...common.observability import get_tracker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the MariaDB Database Inspector Agent using OpenAI Agents SDK. "
                    "Database connection is configured via environment variables (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_DATABASE)."
    )
    parser.add_argument(
        "query",
        nargs="?",
        type=str,
        default=None,
        help="SQL query to execute or question about the database (e.g., 'SELECT * FROM information_schema.tables', 'What tables are in the database?')"
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=100,
        help="Maximum number of rows to return (default: 100)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Query timeout in seconds (default: 10)",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=10,
        help="Maximum number of agent turns/tool calls (default: 10)",
    )
    return parser.parse_args(argv)


async def run_agent_async(
    query: str | None = None,
    max_rows: int = 100,
    timeout: int = 10,
    max_turns: int = 10,
) -> str:
    """
    Run the database inspector agent asynchronously.
    
    Args:
        query: SQL query to execute or question about the database
        max_rows: Maximum number of rows to return
        timeout: Query timeout in seconds
        max_turns: Maximum number of agent turns/tool calls
    
    Returns:
        Final output from the agent
    """
    # Set OpenAI API key
    cfg = OpenAIConfig.from_env()
    set_default_openai_key(cfg.api_key)
    
    # Create the agent
    agent = create_database_inspector_agent()
    
    # Create the user prompt
    if query:
        user_prompt = f"Execute this SQL query or answer this question: {query}"
    else:
        user_prompt = "Please help me explore the database. What would you like to know?"
    
    # Run the agent
    result = await Runner.run(agent, user_prompt, max_turns=max_turns)
    
    # Track observability metrics
    tracker = get_tracker()
    metrics = tracker.track_interaction(
        user_input=user_prompt,
        result=result,
    )
    
    return result.final_output or "No output generated."


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    
    try:
        # Run the agent
        report = asyncio.run(
            run_agent_async(
                query=args.query,
                max_rows=args.max_rows,
                timeout=args.timeout,
                max_turns=args.max_turns,
            )
        )
        
        print("\n===== Database Inspector Results =====\n")
        print(report)
        print("\n======================================\n")
        
        return 0
        
    except Exception as e:
        logging.error(f"Error running agent: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

