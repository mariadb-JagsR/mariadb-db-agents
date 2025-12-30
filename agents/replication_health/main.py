# agents/replication_health/main.py
"""CLI entry point for the Replication Health Agent."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from agents import Runner, set_default_openai_key
from ...common.config import OpenAIConfig
from .agent import create_replication_health_agent
from ...common.observability import get_tracker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the MariaDB Replication Health Agent using OpenAI Agents SDK. "
                    "Database connection is configured via environment variables (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_DATABASE)."
    )
    parser.add_argument(
        "--max-executions",
        type=int,
        default=10,
        help="Maximum number of times to execute SHOW ALL SLAVES STATUS to discover replicas (default: 10). "
             "SkySQL has a maximum of 5 replicas, so 10 executions ensures coverage.",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=30,
        help="Maximum number of agent turns/tool calls (default: 30). Increase if agent needs more steps to complete analysis.",
    )
    return parser.parse_args(argv)


async def run_agent_async(
    max_executions: int = 10,
    max_turns: int = 30,
) -> str:
    """
    Run the replication health agent asynchronously.
    
    Args:
        max_executions: Number of times to execute SHOW ALL SLAVES STATUS to discover replicas
        max_turns: Maximum number of agent turns/tool calls
    
    Returns:
        Final output from the agent
    """
    # Set OpenAI API key
    cfg = OpenAIConfig.from_env()
    set_default_openai_key(cfg.api_key)
    
    # Create the agent
    agent = create_replication_health_agent()
    
    # Create the user prompt
    user_prompt = (
        f"Please check the replication health of this database. "
        f"Analyze all replicas, check for lag, errors, and provide recommendations. "
        f"Use max_executions={max_executions} when calling get_all_replica_status."
    )
    
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
                max_executions=args.max_executions,
                max_turns=args.max_turns,
            )
        )
        
        print("\n===== Replication Health Report =====\n")
        print(report)
        print("\n=====================================\n")
        
        return 0
        
    except Exception as e:
        logging.error(f"Error running agent: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

