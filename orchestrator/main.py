# orchestrator/main.py
"""CLI entry point for the DBA Orchestrator Agent."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from agents import Runner, set_default_openai_key
from ..common.config import OpenAIConfig
from .agent import create_orchestrator_agent
from ..common.observability import get_tracker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the MariaDB DBA Orchestrator Agent using OpenAI Agents SDK. "
                    "The orchestrator intelligently routes queries to specialized agents and synthesizes comprehensive reports. "
                    "Database connection is configured via environment variables (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_DATABASE)."
    )
    parser.add_argument(
        "query",
        nargs="?",
        type=str,
        default=None,
        help="User query about database management (e.g., 'Is my database healthy?', 'Analyze slow queries'). "
             "If not provided, will prompt interactively.",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=30,
        help="Maximum number of agent turns/tool calls (default: 30). Increase if orchestrator needs more steps.",
    )
    return parser.parse_args(argv)


async def run_orchestrator_async(
    user_query: str,
    max_turns: int = 30,
) -> str:
    """
    Run the orchestrator agent asynchronously.
    
    Args:
        user_query: User query about database management
        max_turns: Maximum number of agent turns/tool calls
    
    Returns:
        Final output from the orchestrator
    """
    # Set OpenAI API key
    cfg = OpenAIConfig.from_env()
    set_default_openai_key(cfg.api_key)
    
    # Create the orchestrator agent
    agent = create_orchestrator_agent()
    
    # Run the agent
    result = await Runner.run(agent, user_query, max_turns=max_turns)
    
    # Track observability metrics (mark as orchestrator to aggregate sub-agent metrics)
    tracker = get_tracker()
    metrics = tracker.track_interaction(
        user_input=user_query,
        result=result,
        is_orchestrator=True,
    )
    
    return result.final_output or "No output generated."


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    
    # Get user query
    if args.query:
        user_query = args.query
    else:
        # Interactive prompt
        print("MariaDB DBA Orchestrator")
        print("=" * 80)
        print("Ask me anything about your database management!")
        print("Examples:")
        print("  - 'Is my database healthy?'")
        print("  - 'Analyze slow queries from the last hour'")
        print("  - 'What queries are running right now?'")
        print("  - 'Why is my database slow?'")
        print("=" * 80)
        print()
        user_query = input("Your query: ").strip()
        
        if not user_query:
            print("No query provided. Exiting.")
            return 1
    
    try:
        # Run the orchestrator
        report = asyncio.run(
            run_orchestrator_async(
                user_query=user_query,
                max_turns=args.max_turns,
            )
        )
        
        print("\n" + "=" * 80)
        print("ORCHESTRATOR REPORT")
        print("=" * 80 + "\n")
        print(report)
        print("\n" + "=" * 80 + "\n")
        
        return 0
        
    except Exception as e:
        logging.error(f"Error running orchestrator: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

