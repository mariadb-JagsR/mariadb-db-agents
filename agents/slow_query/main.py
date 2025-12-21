# agents/slow_query/main.py
from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from agents import Runner, set_default_openai_key
from ...common.config import OpenAIConfig
from .agent import create_slow_query_agent
from ...common.observability import get_tracker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the MariaDB Slow Query Tuning Agent using OpenAI Agents SDK. "
                    "Database connection is configured via environment variables (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_DATABASE)."
    )
    parser.add_argument(
        "--hours",
        type=float,
        default=1.0,
        help="Approximate time window in hours to analyze slow queries.",
    )
    parser.add_argument(
        "--max-patterns",
        type=int,
        default=8,
        help="Maximum number of query patterns to deep-analyze.",
    )
    return parser.parse_args(argv)


async def run_agent_async(
    time_window_hours: float,
    max_patterns: int,
) -> str:
    """
    Run the slow query agent asynchronously.

    Args:
        time_window_hours: Time window in hours to analyze
        max_patterns: Maximum number of patterns to analyze

    Returns:
        Final output from the agent
    """
    # Set OpenAI API key
    cfg = OpenAIConfig.from_env()
    set_default_openai_key(cfg.api_key)

    # Create the agent
    agent = create_slow_query_agent()

    # Create the user prompt
    user_prompt = (
        f"Please analyze slow queries for approximately the last {time_window_hours} hour(s). "
        f"Focus on at most {max_patterns} of the most impactful query patterns."
    )

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
                time_window_hours=args.hours,
                max_patterns=args.max_patterns,
            )
        )

        print("\n===== Slow Query Analysis Report =====\n")
        print(report)
        print("\n======================================\n")

        return 0

    except Exception as e:
        logging.error(f"Error running agent: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

