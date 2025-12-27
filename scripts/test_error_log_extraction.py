#!/usr/bin/env python3
"""
Test script for error log pattern extraction.

This script allows you to test the error log pattern extraction functionality
with sample error logs before using it in the Incident Triage Agent.
"""

import sys
import json
from pathlib import Path

# Add parent directory to path to import from common
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import from common module
from common.db_client import (
    tail_error_log_file,
    extract_error_log_patterns,
)


def test_pattern_extraction_from_file(log_path: str, max_patterns: int = 20):
    """
    Test pattern extraction from a local error log file.
    
    Args:
        log_path: Path to error log file
        max_patterns: Maximum number of patterns to extract
    """
    print(f"\n{'='*80}")
    print(f"Testing Error Log Pattern Extraction")
    print(f"{'='*80}")
    print(f"\nLog file: {log_path}")
    print(f"Max patterns: {max_patterns}\n")
    
    try:
        # Read the file content
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        print(f"File size: {len(content)} bytes")
        print(f"Total lines: {len(content.splitlines())}\n")
        
        # Extract patterns
        print("Extracting patterns...")
        patterns = extract_error_log_patterns(content, max_patterns=max_patterns)
        
        print(f"\n{'='*80}")
        print(f"Found {len(patterns)} unique error patterns")
        print(f"{'='*80}\n")
        
        # Display patterns
        for i, pattern in enumerate(patterns, 1):
            print(f"\nPattern #{i}:")
            print(f"  Severity: {pattern['severity']}")
            print(f"  Count: {pattern['count']}")
            print(f"  First seen: {pattern['first_seen'] or 'N/A'}")
            print(f"  Last seen: {pattern['last_seen'] or 'N/A'}")
            print(f"  Pattern: {pattern['pattern'][:200]}...")
            print(f"  Sample message: {pattern['sample_message'][:200]}...")
        
        # Summary statistics
        print(f"\n{'='*80}")
        print("Summary Statistics")
        print(f"{'='*80}")
        
        severity_counts = {}
        total_errors = 0
        for pattern in patterns:
            severity = pattern['severity']
            severity_counts[severity] = severity_counts.get(severity, 0) + pattern['count']
            total_errors += pattern['count']
        
        print(f"\nTotal error occurrences: {total_errors}")
        print(f"\nBy severity:")
        for severity, count in sorted(severity_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {severity}: {count} occurrences")
        
        # Save to JSON for inspection
        output_file = Path(log_path).with_suffix('.patterns.json')
        with open(output_file, 'w') as f:
            json.dump(patterns, f, indent=2)
        print(f"\nPatterns saved to: {output_file}")
        
        return patterns
        
    except FileNotFoundError:
        print(f"ERROR: File not found: {log_path}")
        return None
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_tail_error_log_file(log_path: str, max_bytes: int = 1000000, tail_lines: int = 5000):
    """
    Test the tail_error_log_file function with pattern extraction.
    
    Args:
        log_path: Path to error log file
        max_bytes: Maximum bytes to read
        tail_lines: Maximum lines to read
    """
    print(f"\n{'='*80}")
    print(f"Testing tail_error_log_file with Pattern Extraction")
    print(f"{'='*80}")
    print(f"\nLog file: {log_path}")
    print(f"Max bytes: {max_bytes}")
    print(f"Tail lines: {tail_lines}\n")
    
    try:
        result = tail_error_log_file(
            path=log_path,
            max_bytes=max_bytes,
            tail_lines=tail_lines,
            extract_patterns=True,
            max_patterns=20,
        )
        
        print(f"Source: {result['source']}")
        print(f"Total lines processed: {result['total_lines']}")
        print(f"Patterns found: {len(result['patterns'])}\n")
        
        # Display top patterns
        print("Top Error Patterns:")
        for i, pattern in enumerate(result['patterns'][:10], 1):
            print(f"\n  {i}. [{pattern['severity']}] Count: {pattern['count']}")
            print(f"     Pattern: {pattern['pattern'][:150]}...")
        
        return result
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Test error log pattern extraction with sample logs"
    )
    parser.add_argument(
        "log_file",
        help="Path to error log file to test"
    )
    parser.add_argument(
        "--max-patterns",
        type=int,
        default=20,
        help="Maximum number of patterns to extract (default: 20)"
    )
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=1000000,
        help="Maximum bytes to read from log file (default: 1000000)"
    )
    parser.add_argument(
        "--tail-lines",
        type=int,
        default=5000,
        help="Maximum lines to read from tail (default: 5000)"
    )
    parser.add_argument(
        "--test-tail",
        action="store_true",
        help="Also test the tail_error_log_file function"
    )
    
    args = parser.parse_args()
    
    # Test pattern extraction
    patterns = test_pattern_extraction_from_file(
        args.log_file,
        max_patterns=args.max_patterns
    )
    
    # Test tail function if requested
    if args.test_tail:
        result = test_tail_error_log_file(
            args.log_file,
            max_bytes=args.max_bytes,
            tail_lines=args.tail_lines
        )
    
    print(f"\n{'='*80}")
    print("Test completed!")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()

