# agents/incident_triage/main.py
from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from agents import Runner, set_default_openai_key
from ...common.config import OpenAIConfig
from .agent import create_incident_triage_agent
from ...common.observability import get_tracker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    import os
    
    parser = argparse.ArgumentParser(
        description="Run the MariaDB Incident Triage Agent using OpenAI Agents SDK. "
                    "Database connection is configured via environment variables (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_DATABASE)."
    )
    parser.add_argument(
        "--error-log-path",
        type=str,
        default=None,
        help="Path to error log file (for local file access). If not provided, will attempt SkySQL API if service_id is set.",
    )
    parser.add_argument(
        "--service-id",
        type=str,
        default=os.getenv("SKYSQL_SERVICE_ID"),
        help="SkySQL service ID for API-based error log access (if not using local file). "
             "Can also be set via SKYSQL_SERVICE_ID environment variable.",
    )
    parser.add_argument(
        "--max-error-patterns",
        type=int,
        default=20,
        help="Maximum number of error patterns to extract from error log (default: 20).",
    )
    parser.add_argument(
        "--error-log-lines",
        type=int,
        default=5000,
        help="Number of lines to read from error log tail (default: 5000).",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=30,
        help="Maximum number of agent turns/tool calls (default: 30). Increase if agent needs more steps to complete analysis.",
    )
    return parser.parse_args(argv)


async def run_agent_async(
    error_log_path: str | None = None,
    service_id: str | None = None,
    max_error_patterns: int = 20,
    error_log_lines: int = 5000,
    max_turns: int = 30,
) -> str:
    """
    Run the incident triage agent asynchronously.

    Args:
        error_log_path: Path to error log file (for local access)
        service_id: SkySQL service ID (for API access)
        max_error_patterns: Maximum error patterns to extract
        error_log_lines: Lines to read from error log
        max_turns: Maximum number of agent turns/tool calls

    Returns:
        Final output from the agent
    """
    # Set OpenAI API key
    cfg = OpenAIConfig.from_env()
    set_default_openai_key(cfg.api_key)

    # Create the agent
    agent = create_incident_triage_agent()

    # Create the user prompt
    user_prompt = (
        "Something's wrong with the database. Please perform incident triage: "
        "gather a health snapshot, identify the top 2-3 likely causes, and provide "
        "a prioritized checklist of immediate checks and safe mitigations."
    )
    
    # Add error log context if provided
    if error_log_path:
        user_prompt += f"\n\nError log is available at: {error_log_path}"
    elif service_id:
        user_prompt += f"\n\nError log should be fetched via SkySQL API for service_id: {service_id}"

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
        # Run the async agent
        report = asyncio.run(
            run_agent_async(
                error_log_path=args.error_log_path,
                service_id=args.service_id,
                max_error_patterns=args.max_error_patterns,
                error_log_lines=args.error_log_lines,
                max_turns=args.max_turns,
            )
        )

        print("\n===== Incident Triage Report =====\n")
        print(report)
        print("\n===================================\n")

        return 0

    except Exception as e:
        logging.error(f"Error running agent: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

