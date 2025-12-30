# agents/database_inspector/__init__.py
"""Database Inspector Agent - Execute read-only SQL queries."""

from .agent import create_database_inspector_agent

__all__ = ["create_database_inspector_agent"]

