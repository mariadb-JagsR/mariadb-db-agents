# agents/replication_health/__init__.py
"""Replication Health Agent - Monitors replication lag and health."""

from .agent import create_replication_health_agent

__all__ = ["create_replication_health_agent"]

