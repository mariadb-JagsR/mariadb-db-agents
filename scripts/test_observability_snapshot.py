#!/usr/bin/env python3
"""
Quick test script for MariaDB Cloud observability snapshot + history tools.

Usage:
    python scripts/test_observability_snapshot.py
    python scripts/test_observability_snapshot.py --hours 6
    python scripts/test_observability_snapshot.py --query 'max(mariadb_global_status_threads_running{mariadb="my-service"})' --hours 6
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.observability_tools import (
    METRIC_CATALOG,
    get_mariadb_cloud_observability_snapshot_impl,
    query_mariadb_cloud_observability_metrics_impl,
)


def _print_snapshot(result: dict) -> None:
    snapshot = result.get("snapshot", {}) or {}
    print(f"Namespace: {result.get('namespace')}")
    print(f"Service name: {result.get('service_name')}")
    print(f"Region: {result.get('region')}")
    print()

    disks = snapshot.get("disk", [])
    if disks:
        print("Disk Utilization:")
        for disk in disks:
            print(
                f"  {disk['server_name']:35s} {disk['disk_purpose']:10s} "
                f"{disk['utilization_pct']:6.2f}%  "
                f"used={disk['used_bytes']:.0f}  cap={disk['capacity_bytes']:.0f}"
            )
    else:
        print("Disk Utilization: (no volume stats found)")
    print()

    cpu = snapshot.get("cpu", {})
    if isinstance(cpu, dict) and "cpu_pct_est" in cpu:
        print(f"CPU: {cpu['cpu_pct_est']:.1f}%")
    else:
        print(f"CPU: {cpu}")
    print()

    print(f"Threads Connected (max): {snapshot.get('threads_connected_max')}")
    print(f"Threads Running (max): {snapshot.get('threads_running_max')}")
    print(f"Aborted Clients (max): {snapshot.get('aborted_clients_max')}")
    print(f"Aborted Connects (max): {snapshot.get('aborted_connects_max')}")
    print()

    warnings = result.get("warnings", [])
    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"  - {warning}")
    else:
        print("Warnings: (none)")
    print()


def _print_history(result: dict) -> None:
    history = result.get("history") or {}
    metrics = history.get("metrics") or {}
    if not metrics:
        print("History: (none)")
        return

    print(
        f"History ({history.get('hours')}h, step={history.get('step_seconds')}s, "
        f"{history.get('start_time')} -> {history.get('end_time')}):"
    )
    for key, payload in metrics.items():
        label = payload.get("label", key)
        if not payload.get("available"):
            print(f"  - {label}: unavailable ({payload.get('message', 'no data')})")
            continue
        series = payload.get("series") or []
        if not series:
            print(f"  - {label}: no series")
            continue
        summary = series[0].get("summary") or {}
        print(
            f"  - {label}: min={summary.get('min')} max={summary.get('max')} "
            f"avg={summary.get('avg'):.2f} last={summary.get('last')} "
            f"points={summary.get('point_count')}"
        )
    print()


def _print_custom_query(result: dict) -> None:
    print(f"Query type: {result.get('query_type')}")
    print(f"Query: {result.get('query')}")
    if result.get("query_type") == "range":
        for series in result.get("series") or []:
            summary = series.get("summary") or {}
            print(
                f"  {series.get('metric')}: min={summary.get('min')} max={summary.get('max')} "
                f"last={summary.get('last')} points={summary.get('point_count')}"
            )
    else:
        for sample in result.get("samples") or []:
            print(f"  {sample.get('metric')}: {sample.get('value')}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Test MariaDB Cloud observability snapshot/history tools")
    parser.add_argument("--hours", type=int, default=None, help="Include curated historical metrics")
    parser.add_argument(
        "--metrics",
        nargs="*",
        default=None,
        help=f"Catalog metric keys (default: all). Available: {', '.join(METRIC_CATALOG.keys())}",
    )
    parser.add_argument("--step-seconds", type=int, default=None, help="Range query step size")
    parser.add_argument("--query", default=None, help="Custom PromQL query (uses query endpoint)")
    args = parser.parse_args()

    print("=" * 60)
    print("Testing MariaDB Cloud Observability Tools")
    print("=" * 60)
    print()

    if args.query:
        print("Running custom PromQL query...")
        result = query_mariadb_cloud_observability_metrics_impl(
            args.query,
            hours=args.hours,
            step_seconds=args.step_seconds,
        )
    else:
        print("Fetching observability snapshot...")
        if args.hours:
            print(f"Including curated history for the last {args.hours} hour(s)")
        print()
        result = get_mariadb_cloud_observability_snapshot_impl(
            hours=args.hours,
            metric_names=args.metrics,
            step_seconds=args.step_seconds,
        )

    if not result.get("available"):
        print("Failed to fetch observability data")
        print()
        print(f"Error: {result.get('message', 'Unknown error')}")
        print()
        print("Make sure:")
        print("  - MARIADB_CLOUD_API_KEY is set in the environment")
        print("  - DB_HOST or MARIADB_CLOUD_SERVICE_ID identifies the target service")
        print("  - You have access to the MariaDB Cloud provisioning and observability APIs")
        return 1

    print("Successfully fetched observability data!")
    print()
    if args.query:
        _print_custom_query(result)
    else:
        _print_snapshot(result)
        if args.hours:
            _print_history(result)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
