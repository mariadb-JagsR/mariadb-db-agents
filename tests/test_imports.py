#!/usr/bin/env python3
"""
Basic import tests to verify all modules can be imported correctly.
"""

import sys
import importlib


def test_imports():
    """Test that all key modules can be imported."""
    modules_to_test = [
        "mariadb_db_agents",
        "mariadb_db_agents.common.config",
        "mariadb_db_agents.common.db_client",
        "mariadb_db_agents.common.guardrails",
        "mariadb_db_agents.common.observability",
        "mariadb_db_agents.common.performance_metrics",
        "mariadb_db_agents.common.performance_tools",
        "mariadb_db_agents.agents.slow_query.agent",
        "mariadb_db_agents.agents.slow_query.tools",
        "mariadb_db_agents.agents.slow_query.main",
        "mariadb_db_agents.agents.running_query.agent",
        "mariadb_db_agents.agents.running_query.tools",
        "mariadb_db_agents.agents.running_query.main",
        "mariadb_db_agents.cli.main",
    ]
    
    failed = []
    passed = []
    
    for module_name in modules_to_test:
        try:
            importlib.import_module(module_name)
            passed.append(module_name)
            print(f"✓ {module_name}")
        except Exception as e:
            failed.append((module_name, str(e)))
            print(f"✗ {module_name}: {e}")
    
    print(f"\n{'='*60}")
    print(f"Passed: {len(passed)}/{len(modules_to_test)}")
    if failed:
        print(f"Failed: {len(failed)}")
        for module, error in failed:
            print(f"  - {module}: {error}")
        return False
    else:
        print("All imports successful!")
        return True


if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)


