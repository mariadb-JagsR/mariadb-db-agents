#!/usr/bin/env python3
"""Test script for MCP server functionality."""

import asyncio
import sys
from mariadb_db_agents.mcp_server.main import server, list_tools, call_tool


async def test_list_tools():
    """Test listing tools."""
    print("Testing list_tools()...")
    tools = await list_tools()
    print(f"✓ Found {len(tools)} tools:")
    for tool in tools:
        print(f"  - {tool.name}: {tool.description[:60]}...")
    return len(tools) == 6


async def test_call_tool():
    """Test calling a tool (dry run - won't actually execute agents)."""
    print("\nTesting call_tool() with invalid tool...")
    try:
        result = await call_tool("nonexistent_tool", {})
        print(f"✓ Error handling works: {result[0].text[:100]}...")
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("MCP Server Test Suite")
    print("=" * 60)
    
    tests = [
        ("List Tools", test_list_tools),
        ("Call Tool (Error Handling)", test_call_tool),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print(f"✗ {name} failed: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("Test Results:")
    print("=" * 60)
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(result for _, result in results)
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

