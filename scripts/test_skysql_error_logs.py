#!/usr/bin/env python3
"""
Test script for SkySQL API error log integration.

This script tests the SkySQL API error log functionality:
1. API authentication
2. Fetching log info
3. Downloading log archive
4. Pattern extraction from SkySQL logs
5. Integration with tail_error_log_file

Usage:
    # Test with service_id
    python scripts/test_skysql_error_logs.py --service-id <service_id>
    
    # Test with custom time range
    python scripts/test_skysql_error_logs.py --service-id <service_id> --hours 48
    
    # Test API connection only
    python scripts/test_skysql_error_logs.py --service-id <service_id> --test-api-only
"""

import sys
import argparse
import json
from pathlib import Path
from datetime import UTC, datetime, timedelta

# Add parent directory to path to import from common
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import from common module
from common.config import SkySQLConfig
from common.db_client import (
    tail_error_log_file,
    _get_skysql_logs_info,
    _get_skysql_logs_archive,
    _load_skysql_errors,
)


def test_api_config():
    """Test that SkySQL API configuration is available."""
    print(f"\n{'='*80}")
    print("Test 1: SkySQL API Configuration")
    print(f"{'='*80}\n")
    
    try:
        config = SkySQLConfig.from_env()
        print(f"✅ API Key: {'*' * (len(config.api_key) - 8)}{config.api_key[-8:]}")
        print(f"✅ API URL: {config.api_url}")
        return config
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        print("\nMake sure you have set SKYSQL_API_KEY in your .env file")
        return None


def test_api_connection(config: SkySQLConfig, service_id: str):
    """Test API connection by fetching log info."""
    print(f"\n{'='*80}")
    print("Test 2: SkySQL API Connection")
    print(f"{'='*80}\n")
    
    try:
        # Calculate time range (last 24 hours)
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(hours=24)
        
        start_timestamp = start_time.isoformat(timespec="seconds").split("+")[0] + "Z"
        end_timestamp = end_time.isoformat(timespec="seconds").split("+")[0] + "Z"
        
        print(f"Service ID: {service_id}")
        print(f"Time range: {start_timestamp} to {end_timestamp}")
        print(f"\nFetching log info...")
        
        logids = _get_skysql_logs_info(
            api_key=config.api_key,
            service_id=service_id,
            log_type="error-log",
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            api_url=config.api_url,
        )
        
        print(f"✅ Successfully connected to SkySQL API")
        print(f"✅ Found {len(logids)} log file(s)")
        print(f"   Log IDs: {logids[:5]}{'...' if len(logids) > 5 else ''}")
        
        return logids, start_timestamp, end_timestamp
        
    except Exception as e:
        print(f"❌ API connection failed: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None


def test_log_download(config: SkySQLConfig, logids: list[str]):
    """Test downloading log archive."""
    print(f"\n{'='*80}")
    print("Test 3: Download Log Archive")
    print(f"{'='*80}\n")
    
    try:
        print(f"Downloading {len(logids)} log file(s)...")
        
        payload = _get_skysql_logs_archive(
            api_key=config.api_key,
            log_type="error-log",
            logids=logids,
            api_url=config.api_url,
        )
        
        print(f"✅ Successfully downloaded log archive")
        print(f"   Archive size: {len(payload):,} bytes ({len(payload) / 1024 / 1024:.2f} MB)")
        
        return payload
        
    except Exception as e:
        print(f"❌ Log download failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_log_extraction(payload: bytes, start_timestamp: str, end_timestamp: str):
    """Test extracting error log lines from archive."""
    print(f"\n{'='*80}")
    print("Test 4: Extract Error Log Lines")
    print(f"{'='*80}\n")
    
    try:
        print("Extracting error log lines...")
        
        log_lines = _load_skysql_errors(
            payload=payload,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            max_lines=100,  # Limit for testing
        )
        
        print(f"✅ Successfully extracted {len(log_lines)} error log lines")
        
        if log_lines:
            print(f"\nSample log lines (first 3):")
            for i, line in enumerate(log_lines[:3], 1):
                print(f"\n  {i}. {line[:200]}...")
        
        return log_lines
        
    except Exception as e:
        print(f"❌ Log extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_tail_error_log_file(service_id: str, hours: int = 24):
    """Test the full tail_error_log_file function with SkySQL API."""
    print(f"\n{'='*80}")
    print("Test 5: Full Integration Test (tail_error_log_file)")
    print(f"{'='*80}\n")
    
    try:
        print(f"Testing tail_error_log_file with service_id={service_id}")
        print(f"Time range: last {hours} hours")
        print(f"\nFetching and processing error logs...")
        
        result = tail_error_log_file(
            service_id=service_id,
            tail_lines=100,  # Limit for testing
            extract_patterns=True,
            max_patterns=20,
        )
        
        print(f"✅ Successfully processed error logs")
        print(f"   Source: {result['source']}")
        print(f"   Total lines: {result['total_lines']}")
        print(f"   Patterns found: {len(result['patterns'])}")
        
        if result['patterns']:
            print(f"\nTop Error Patterns:")
            for i, pattern in enumerate(result['patterns'][:10], 1):
                print(f"\n  {i}. [{pattern['severity']}] Count: {pattern['count']}")
                print(f"     First seen: {pattern['first_seen'] or 'N/A'}")
                print(f"     Last seen: {pattern['last_seen'] or 'N/A'}")
                print(f"     Pattern: {pattern['pattern'][:150]}...")
        
        # Save results to JSON
        output_file = Path(f"skysql_error_logs_test_{service_id}.json")
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        print(f"\n✅ Results saved to: {output_file}")
        
        return result
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test SkySQL API error log integration"
    )
    parser.add_argument(
        "--service-id",
        type=str,
        required=True,
        help="SkySQL service ID to test"
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=24,
        help="Number of hours to look back for logs (default: 24)"
    )
    parser.add_argument(
        "--test-api-only",
        action="store_true",
        help="Only test API connection, don't download logs"
    )
    parser.add_argument(
        "--skip-full-test",
        action="store_true",
        help="Skip the full integration test"
    )
    
    args = parser.parse_args()
    
    print(f"\n{'='*80}")
    print("SkySQL API Error Log Integration Test")
    print(f"{'='*80}")
    
    # Test 1: Configuration
    config = test_api_config()
    if not config:
        print("\n❌ Configuration test failed. Exiting.")
        return 1
    
    if args.test_api_only:
        # Test 2: API Connection only
        logids, start_timestamp, end_timestamp = test_api_connection(config, args.service_id)
        if logids:
            print("\n✅ API connection test passed!")
        else:
            print("\n❌ API connection test failed!")
            return 1
        return 0
    
    # Test 2: API Connection
    logids, start_timestamp, end_timestamp = test_api_connection(config, args.service_id)
    if not logids:
        print("\n❌ API connection test failed. Exiting.")
        return 1
    
    # Test 3: Download Log Archive
    payload = test_log_download(config, logids)
    if not payload:
        print("\n❌ Log download test failed. Exiting.")
        return 1
    
    # Test 4: Extract Log Lines
    log_lines = test_log_extraction(payload, start_timestamp, end_timestamp)
    if log_lines is None:
        print("\n❌ Log extraction test failed. Exiting.")
        return 1
    
    # Test 5: Full Integration Test
    if not args.skip_full_test:
        result = test_tail_error_log_file(args.service_id, hours=args.hours)
        if not result:
            print("\n❌ Full integration test failed.")
            return 1
    
    print(f"\n{'='*80}")
    print("✅ All tests passed!")
    print(f"{'='*80}\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())


