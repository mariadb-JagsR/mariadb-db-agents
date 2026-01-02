#!/usr/bin/env python3
"""
Quick test script for SkySQL observability snapshot tool.

Usage:
    python -m mariadb_db_agents.scripts.test_observability_snapshot
"""

from __future__ import annotations

import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mariadb_db_agents.common.observability_tools import get_skysql_observability_snapshot


def main():
    print("=" * 60)
    print("Testing SkySQL Observability Snapshot Tool")
    print("=" * 60)
    print()
    
    # Call the tool (it will auto-detect namespace and region from env/config)
    print("Fetching observability snapshot...")
    print("(Will auto-detect service_id and region from environment)")
    print()
    
    result = get_skysql_observability_snapshot()
    
    if result.get("available"):
        print("✅ Successfully fetched observability snapshot!")
        print()
        print(f"Namespace: {result.get('namespace')}")
        print(f"Region: {result.get('region')}")
        print()
        
        snapshot = result.get("snapshot", {})
        
        # Display disk utilization
        disks = snapshot.get("disk", [])
        if disks:
            print("Disk Utilization:")
            for d in disks:
                print(f"  {d['server_name']:35s} {d['disk_purpose']:10s} "
                      f"{d['utilization_pct']:6.2f}%  "
                      f"used={d['used_bytes']:.0f}  cap={d['capacity_bytes']:.0f}")
        else:
            print("Disk Utilization: (no volume stats found)")
        print()
        
        # Display CPU
        cpu = snapshot.get("cpu", {})
        if isinstance(cpu, dict) and "cpu_pct_est" in cpu:
            print(f"CPU: {cpu['cpu_pct_est']:.1f}%")
        else:
            print(f"CPU: {cpu}")
        print()
        
        # Display threads
        print(f"Threads Connected (max): {snapshot.get('threads_connected_max')}")
        print(f"Threads Running (max): {snapshot.get('threads_running_max')}")
        print(f"Aborted Clients (max): {snapshot.get('aborted_clients_max')}")
        print(f"Aborted Connects (max): {snapshot.get('aborted_connects_max')}")
        print()
        
        # Display warnings
        warnings = result.get("warnings", [])
        if warnings:
            print("Warnings:")
            for w in warnings:
                print(f"  - {w}")
        else:
            print("Warnings: (none)")
        print()
        
    else:
        print("❌ Failed to fetch observability snapshot")
        print()
        print(f"Error: {result.get('message', 'Unknown error')}")
        print()
        print("Make sure:")
        print("  - SKYSQL_API_KEY is set in environment")
        print("  - SKYSQL_SERVICE_ID is set (or service_id can be inferred from DB_HOST)")
        print("  - You have access to the SkySQL provisioning and observability APIs")
        return 1
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

