#!/usr/bin/env python3
"""Fetch a MariaDB Cloud observability snapshot and optional metric history."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from common.observability_tools import get_mariadb_cloud_observability_snapshot_impl


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch current and historical MariaDB Cloud observability metrics"
    )
    parser.add_argument("--namespace", help="MariaDB Cloud service ID/namespace")
    parser.add_argument("--service-name", help="MariaDB Cloud service name")
    parser.add_argument(
        "--region",
        choices=["us-central1", "europe-west1", "asia-southeast1"],
        help="Observability region (auto-detected when omitted)",
    )
    parser.add_argument("--server-name", help="Optional server_name label filter")
    parser.add_argument("--hours", type=int, help="Include curated metric history")
    parser.add_argument("--step-seconds", type=int, help="Historical query step")
    parser.add_argument("--metrics", nargs="*", help="Curated metric keys to include")
    args = parser.parse_args()

    result = get_mariadb_cloud_observability_snapshot_impl(
        namespace=args.namespace,
        service_name=args.service_name,
        server_name=args.server_name,
        region=args.region,
        hours=args.hours,
        metric_names=args.metrics,
        step_seconds=args.step_seconds,
    )
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("available") else 1


if __name__ == "__main__":
    raise SystemExit(main())
