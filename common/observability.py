# src/common/observability.py
"""
Observability module for tracking LLM usage, tokens, and round trips.

Tracks:
- Number of LLM round trips (requests)
- Input tokens per request and total
- Output tokens per request and total
- Total tokens (input + output)
- Context size
- Per-interaction metrics
"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from agents import RunResult, Usage

logger = logging.getLogger(__name__)


@dataclass
class InteractionMetrics:
    """Metrics for a single agent interaction."""

    timestamp: datetime
    """When the interaction occurred."""

    user_input: str
    """The user's input message."""

    agent_output: str | None
    """The agent's final output."""

    llm_round_trips: int
    """Number of LLM API calls made."""

    total_input_tokens: int
    """Total input tokens across all requests."""

    total_output_tokens: int
    """Total output tokens across all requests."""

    total_tokens: int
    """Total tokens (input + output)."""

    cached_tokens: int = 0
    """Number of cached tokens (if available)."""

    reasoning_tokens: int = 0
    """Number of reasoning tokens (if available, for o1 models)."""

    per_request_usage: list[dict[str, Any]] = field(default_factory=list)
    """Per-request token breakdown."""

    context_size: int = 0
    """Approximate context size (input tokens)."""

    sub_agent_metrics: list[dict[str, Any]] = field(default_factory=list)
    """Metrics from sub-agents invoked during this interaction (for orchestrator)."""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "user_input": self.user_input[:200] + "..." if len(self.user_input) > 200 else self.user_input,
            "agent_output_length": len(self.agent_output) if self.agent_output else 0,
            "llm_round_trips": self.llm_round_trips,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "cached_tokens": self.cached_tokens,
            "reasoning_tokens": self.reasoning_tokens,
            "context_size": self.context_size,
            "per_request_usage": self.per_request_usage,
            "sub_agent_metrics": self.sub_agent_metrics,
        }
    
    def get_total_with_sub_agents(self) -> dict[str, Any]:
        """Get total metrics including sub-agents (for orchestrator)."""
        total_round_trips = self.llm_round_trips
        total_input_tokens = self.total_input_tokens
        total_output_tokens = self.total_output_tokens
        total_tokens = self.total_tokens
        total_cached_tokens = self.cached_tokens
        total_reasoning_tokens = self.reasoning_tokens
        
        for sub_metric in self.sub_agent_metrics:
            total_round_trips += sub_metric.get("llm_round_trips", 0)
            total_input_tokens += sub_metric.get("total_input_tokens", 0)
            total_output_tokens += sub_metric.get("total_output_tokens", 0)
            total_tokens += sub_metric.get("total_tokens", 0)
            total_cached_tokens += sub_metric.get("cached_tokens", 0)
            total_reasoning_tokens += sub_metric.get("reasoning_tokens", 0)
        
        return {
            "orchestrator_round_trips": self.llm_round_trips,
            "orchestrator_input_tokens": self.total_input_tokens,
            "orchestrator_output_tokens": self.total_output_tokens,
            "orchestrator_tokens": self.total_tokens,
            "sub_agents_count": len(self.sub_agent_metrics),
            "total_round_trips": total_round_trips,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_tokens": total_tokens,
            "total_cached_tokens": total_cached_tokens,
            "total_reasoning_tokens": total_reasoning_tokens,
            "sub_agent_breakdown": self.sub_agent_metrics,
        }

    def __str__(self) -> str:
        """Human-readable string representation."""
        return (
            f"InteractionMetrics(\n"
            f"  Round trips: {self.llm_round_trips}\n"
            f"  Input tokens: {self.total_input_tokens:,}\n"
            f"  Output tokens: {self.total_output_tokens:,}\n"
            f"  Total tokens: {self.total_tokens:,}\n"
            f"  Cached tokens: {self.cached_tokens:,}\n"
            f"  Reasoning tokens: {self.reasoning_tokens:,}\n"
            f"  Context size: {self.context_size:,}\n"
            f")"
        )


class ObservabilityTracker:
    """Tracks observability metrics for agent interactions."""

    def __init__(
        self,
        log_file: str | Path | None = None,
        log_to_console: bool = True,
        log_to_file: bool = True,
    ):
        """
        Initialize the observability tracker.

        Args:
            log_file: Path to JSON log file. If None, uses default location.
            log_to_console: Whether to print metrics to console.
            log_to_file: Whether to write metrics to file.
        """
        self.log_to_console = log_to_console
        self.log_to_file = log_to_file
        self.interactions: list[InteractionMetrics] = []

        if log_file:
            self.log_file = Path(log_file)
        else:
            # Default: .observability_log.json in the project root
            # From common/observability.py, go up one level to project root
            self.log_file = Path(__file__).parent.parent / ".observability_log.json"

        # Ensure log file directory exists
        if self.log_to_file:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def track_interaction(
        self,
        user_input: str,
        result: RunResult,
        agent_output: str | None = None,
        is_orchestrator: bool = False,
    ) -> InteractionMetrics:
        """
        Track metrics for a single agent interaction.

        Args:
            user_input: The user's input message.
            result: The RunResult from the agent execution.
            agent_output: Optional agent output (will extract from result if not provided).
            is_orchestrator: If True, will aggregate sub-agent metrics for orchestrator.

        Returns:
            InteractionMetrics object with all tracked metrics.
        """
        usage: Usage = result.context_wrapper.usage

        # Extract per-request usage
        per_request = []
        for req_usage in usage.request_usage_entries:
            per_request.append({
                "input_tokens": req_usage.input_tokens,
                "output_tokens": req_usage.output_tokens,
                "total_tokens": req_usage.total_tokens,
                "cached_tokens": req_usage.input_tokens_details.cached_tokens or 0,
                "reasoning_tokens": req_usage.output_tokens_details.reasoning_tokens or 0,
            })

        # Get agent output if not provided
        if agent_output is None:
            agent_output = str(result.final_output) if result.final_output else None

        # Calculate context size (approximate - input tokens)
        context_size = usage.input_tokens

        # Get sub-agent metrics if this is an orchestrator
        sub_agent_metrics = []
        if is_orchestrator:
            sub_agent_metrics = get_orchestrator_sub_agent_metrics()
            # Clear after retrieving (for next orchestrator run)
            clear_orchestrator_sub_agent_metrics()

        metrics = InteractionMetrics(
            timestamp=datetime.now(),
            user_input=user_input,
            agent_output=agent_output,
            llm_round_trips=usage.requests,
            total_input_tokens=usage.input_tokens,
            total_output_tokens=usage.output_tokens,
            total_tokens=usage.total_tokens,
            cached_tokens=usage.input_tokens_details.cached_tokens or 0,
            reasoning_tokens=usage.output_tokens_details.reasoning_tokens or 0,
            per_request_usage=per_request,
            context_size=context_size,
            sub_agent_metrics=sub_agent_metrics,
        )

        self.interactions.append(metrics)

        # Log metrics
        if self.log_to_console:
            self._log_to_console(metrics)

        if self.log_to_file:
            self._log_to_file(metrics)

        return metrics

    def _log_to_console(self, metrics: InteractionMetrics) -> None:
        """Print metrics to console."""
        print("\n" + "=" * 80)
        print("📊 LLM Usage Metrics")
        print("=" * 80)
        
        # Check if this is an orchestrator with sub-agents
        if metrics.sub_agent_metrics:
            totals = metrics.get_total_with_sub_agents()
            print("ORCHESTRATOR (Total across all agents):")
            print(f"  Total round trips: {totals['total_round_trips']}")
            print(f"  Total input tokens: {totals['total_input_tokens']:,}")
            print(f"  Total output tokens: {totals['total_output_tokens']:,}")
            print(f"  Total tokens: {totals['total_tokens']:,}")
            if totals['total_cached_tokens'] > 0:
                print(f"  Total cached tokens: {totals['total_cached_tokens']:,}")
            if totals['total_reasoning_tokens'] > 0:
                print(f"  Total reasoning tokens: {totals['total_reasoning_tokens']:,}")
            print()
            print("Breakdown:")
            print(f"  Orchestrator: {totals['orchestrator_round_trips']} round trips, {totals['orchestrator_tokens']:,} tokens")
            print(f"  Sub-agents ({totals['sub_agents_count']}):")
            for sub_metric in metrics.sub_agent_metrics:
                agent_name = sub_metric.get("agent_name", "unknown")
                print(f"    - {agent_name}: {sub_metric.get('llm_round_trips', 0)} round trips, {sub_metric.get('total_tokens', 0):,} tokens")
        else:
            # Regular agent (no sub-agents)
            print(f"Round trips: {metrics.llm_round_trips}")
            print(f"Input tokens: {metrics.total_input_tokens:,}")
            print(f"Output tokens: {metrics.total_output_tokens:,}")
            print(f"Total tokens: {metrics.total_tokens:,}")
            if metrics.cached_tokens > 0:
                print(f"Cached tokens: {metrics.cached_tokens:,}")
            if metrics.reasoning_tokens > 0:
                print(f"Reasoning tokens: {metrics.reasoning_tokens:,}")
            print(f"Context size: {metrics.context_size:,}")

        if metrics.per_request_usage:
            print("\nPer-request breakdown:")
            for i, req in enumerate(metrics.per_request_usage, 1):
                print(
                    f"  Request {i}: {req['input_tokens']:,} in, "
                    f"{req['output_tokens']:,} out, "
                    f"{req['total_tokens']:,} total"
                )
        print("=" * 80 + "\n")

    def _log_to_file(self, metrics: InteractionMetrics) -> None:
        """Append metrics to JSON log file."""
        try:
            # Read existing logs
            if self.log_file.exists():
                with open(self.log_file, "r") as f:
                    logs = json.load(f)
            else:
                logs = []

            # Append new metrics
            logs.append(metrics.to_dict())

            # Write back
            with open(self.log_file, "w") as f:
                json.dump(logs, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to write observability log: {e}")

    def get_summary(self) -> dict[str, Any]:
        """Get summary statistics across all tracked interactions."""
        if not self.interactions:
            return {
                "total_interactions": 0,
                "total_round_trips": 0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_tokens": 0,
            }

        return {
            "total_interactions": len(self.interactions),
            "total_round_trips": sum(m.llm_round_trips for m in self.interactions),
            "total_input_tokens": sum(m.total_input_tokens for m in self.interactions),
            "total_output_tokens": sum(m.total_output_tokens for m in self.interactions),
            "total_tokens": sum(m.total_tokens for m in self.interactions),
            "avg_round_trips_per_interaction": sum(m.llm_round_trips for m in self.interactions) / len(self.interactions),
            "avg_tokens_per_interaction": sum(m.total_tokens for m in self.interactions) / len(self.interactions),
        }

    def print_summary(self) -> None:
        """Print summary statistics."""
        summary = self.get_summary()
        print("\n" + "=" * 80)
        print("📈 Observability Summary")
        print("=" * 80)
        print(f"Total interactions: {summary['total_interactions']}")
        print(f"Total round trips: {summary['total_round_trips']}")
        print(f"Total input tokens: {summary['total_input_tokens']:,}")
        print(f"Total output tokens: {summary['total_output_tokens']:,}")
        print(f"Total tokens: {summary['total_tokens']:,}")
        if summary['total_interactions'] > 0:
            print(f"Avg round trips/interaction: {summary['avg_round_trips_per_interaction']:.2f}")
            print(f"Avg tokens/interaction: {summary['avg_tokens_per_interaction']:.1f}")
        print("=" * 80 + "\n")


# Global tracker instance (can be shared across conversations)
_global_tracker: ObservabilityTracker | None = None

# Thread-local storage for orchestrator sub-agent metrics
_orchestrator_sub_agent_metrics: dict[int, list[dict[str, Any]]] = {}
_orchestrator_lock = threading.Lock()


def get_tracker() -> ObservabilityTracker:
    """Get or create the global observability tracker."""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = ObservabilityTracker()
    return _global_tracker


def reset_tracker() -> None:
    """Reset the global tracker (useful for testing or new sessions)."""
    global _global_tracker
    _global_tracker = None


def get_orchestrator_sub_agent_metrics() -> list[dict[str, Any]]:
    """Get sub-agent metrics for the current orchestrator execution."""
    thread_id = threading.current_thread().ident
    with _orchestrator_lock:
        return _orchestrator_sub_agent_metrics.get(thread_id, [])


def add_orchestrator_sub_agent_metric(agent_name: str, metrics: dict[str, Any]) -> None:
    """Add sub-agent metrics for the current orchestrator execution."""
    thread_id = threading.current_thread().ident
    with _orchestrator_lock:
        if thread_id not in _orchestrator_sub_agent_metrics:
            _orchestrator_sub_agent_metrics[thread_id] = []
        metrics_with_name = {**metrics, "agent_name": agent_name}
        _orchestrator_sub_agent_metrics[thread_id].append(metrics_with_name)


def clear_orchestrator_sub_agent_metrics() -> None:
    """Clear sub-agent metrics for the current orchestrator execution."""
    thread_id = threading.current_thread().ident
    with _orchestrator_lock:
        if thread_id in _orchestrator_sub_agent_metrics:
            del _orchestrator_sub_agent_metrics[thread_id]

