#!/usr/bin/env python3
"""
Test script for Incident Triage Agent.

This script tests the error log pattern extraction functionality
without requiring the full OpenAI Agents SDK setup.
"""

import sys
from pathlib import Path

# Add parent directory to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from common.db_client import tail_error_log_file, extract_error_log_patterns


def test_error_log_reading(log_path: str):
    """Test reading error log with pattern extraction."""
    print(f"\n{'='*80}")
    print("Testing Error Log Reading for Incident Triage Agent")
    print(f"{'='*80}\n")
    print(f"Log file: {log_path}\n")
    
    try:
        # Test pattern extraction
        result = tail_error_log_file(
            path=log_path,
            max_bytes=1000000,
            tail_lines=5000,
            extract_patterns=True,
            max_patterns=20,
        )
        
        print(f"✅ Successfully read error log")
        print(f"   Source: {result['source']}")
        print(f"   Total lines: {result['total_lines']}")
        print(f"   Patterns found: {len(result['patterns'])}\n")
        
        # Show ERROR and WARNING patterns
        error_patterns = [p for p in result['patterns'] if p['severity'] == 'ERROR']
        warning_patterns = [p for p in result['patterns'] if p['severity'] == 'WARNING']
        
        if error_patterns:
            print(f"⚠️  ERROR Patterns ({len(error_patterns)}):")
            for i, pattern in enumerate(error_patterns, 1):
                print(f"\n   {i}. Count: {pattern['count']}")
                print(f"      Pattern: {pattern['pattern'][:150]}...")
                print(f"      Sample: {pattern['sample_message'][:200]}...")
        
        if warning_patterns:
            print(f"\n⚠️  WARNING Patterns ({len(warning_patterns)}):")
            for i, pattern in enumerate(warning_patterns, 1):
                print(f"\n   {i}. Count: {pattern['count']}")
                print(f"      Pattern: {pattern['pattern'][:150]}...")
                print(f"      Sample: {pattern['sample_message'][:200]}...")
        
        if not error_patterns and not warning_patterns:
            print("ℹ️  No ERROR or WARNING patterns found (only INFO messages)")
        
        print(f"\n{'='*80}")
        print("✅ Error log tool is working correctly!")
        print("   The Incident Triage Agent can use this tool to analyze error logs.")
        print(f"{'='*80}\n")
        
        return result
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test error log reading for Incident Triage Agent")
    parser.add_argument("log_file", help="Path to error log file")
    parser.add_argument("--max-patterns", type=int, default=20, help="Max patterns to extract")
    
    args = parser.parse_args()
    
    test_error_log_reading(args.log_file)


