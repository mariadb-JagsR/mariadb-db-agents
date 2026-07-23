#!/usr/bin/env python3
"""Integration test for MariaDB Cloud error-log API access."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from common.config import MariaDBCloudConfig
from common.db_client import (
    _get_mariadb_cloud_logs_archive,
    _get_mariadb_cloud_logs_info,
    _load_mariadb_cloud_errors,
    extract_error_log_patterns,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Test MariaDB Cloud API error-log integration"
    )
    parser.add_argument(
        "--service-id",
        help="MariaDB Cloud service ID (defaults to MARIADB_CLOUD_SERVICE_ID)",
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=24,
        help="Number of hours to inspect (default: 24)",
    )
    parser.add_argument(
        "--test-api-only",
        action="store_true",
        help="Fetch log metadata without downloading the archive",
    )
    parser.add_argument("--max-lines", type=int, default=100)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    config = MariaDBCloudConfig.from_env()
    service_id = args.service_id or config.service_id
    if not service_id:
        parser.error(
            "--service-id or MARIADB_CLOUD_SERVICE_ID is required"
        )

    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(hours=max(1, args.hours))
    start_timestamp = start_time.isoformat(timespec="seconds").replace("+00:00", "Z")
    end_timestamp = end_time.isoformat(timespec="seconds").replace("+00:00", "Z")

    print("MariaDB Cloud Error Log API Integration Test")
    print(f"Service ID: {service_id}")
    print(f"Time range: {start_timestamp} to {end_timestamp}")

    log_ids = _get_mariadb_cloud_logs_info(
        api_key=config.api_key,
        service_id=service_id,
        log_type="error-log",
        start_timestamp=start_timestamp,
        end_timestamp=end_timestamp,
        api_url=config.api_url,
    )
    print(f"Found {len(log_ids)} log archive item(s)")
    if args.test_api_only:
        return 0

    payload = _get_mariadb_cloud_logs_archive(
        api_key=config.api_key,
        log_type="error-log",
        logids=log_ids,
        api_url=config.api_url,
    )
    print(f"Downloaded {len(payload):,} bytes")

    lines = _load_mariadb_cloud_errors(
        payload=payload,
        start_timestamp=start_timestamp,
        end_timestamp=end_timestamp,
        max_lines=args.max_lines,
    )
    patterns = extract_error_log_patterns("\n".join(lines), max_patterns=20)
    result = {
        "source": "mariadb_cloud_api",
        "service_id": service_id,
        "start_time": start_timestamp,
        "end_time": end_timestamp,
        "total_lines": len(lines),
        "patterns": patterns,
    }
    print(f"Extracted {len(lines)} lines and {len(patterns)} pattern(s)")

    if args.output:
        args.output.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
        print(f"Saved results to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
