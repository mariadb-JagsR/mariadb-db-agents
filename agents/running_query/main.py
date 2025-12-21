# agents/running_query/main.py
from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from agents import Runner, set_default_openai_key
from ...common.config import OpenAIConfig
from .agent import create_running_query_agent
from ...common.observability import get_tracker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the MariaDB Running Query Analysis Agent using OpenAI Agents SDK. "
                    "Database connection is configured via environment variables (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_DATABASE)."
    )
    parser.add_argument(
        "--min-time-seconds",
        type=float,
        default=1.0,
        help="Minimum query execution time in seconds to analyze (default: 1.0).",
    )
    parser.add_argument(
        "--include-sleeping",
        action="store_true",
        help="Include sleeping/idle connections in the analysis.",
    )
    parser.add_argument(
        "--max-queries",
        type=int,
        default=20,
        help="Maximum number of queries to analyze in detail (default: 20).",
    )
    return parser.parse_args(argv)


async def run_agent_async(
    min_time_seconds: float,
    include_sleeping: bool,
    max_queries: int,
) -> str:
    """
    Run the running query agent asynchronously.

    Args:
        min_time_seconds: Minimum query execution time to analyze
        include_sleeping: Whether to include sleeping connections
        max_queries: Maximum number of queries to analyze in detail

    Returns:
        Final output from the agent
    """
    # Set OpenAI API key
    cfg = OpenAIConfig.from_env()
    set_default_openai_key(cfg.api_key)

    # Create the agent
    agent = create_running_query_agent()

    # Create the user prompt
    user_prompt = (
        f"Please analyze currently running queries. "
        f"Focus on queries that have been running for at least {min_time_seconds} second(s). "
    )
    if include_sleeping:
        user_prompt += "Include sleeping/idle connections in the analysis. "
    else:
        user_prompt += "Exclude sleeping/idle connections. "
    
    user_prompt += f"Analyze at most {max_queries} of the most problematic queries in detail."

    # Run the agent
    result = await Runner.run(agent, user_prompt)

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
        # Run the async agent
        report = asyncio.run(
            run_agent_async(
                min_time_seconds=args.min_time_seconds,
                include_sleeping=args.include_sleeping,
                max_queries=args.max_queries,
            )
        )

        print("\n===== Running Query Analysis Report =====\n")
        print(report)
        print("\n==========================================\n")

        return 0

    except Exception as e:
        logging.error(f"Error running agent: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

