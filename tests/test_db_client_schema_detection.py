"""
Unit tests for schema detection via information_schema (no live DB).

``detect_table_database`` issues queries in a fixed order:
1. If the SQL references ``mysql.<table>``, a probe for tables that exist in schema ``mysql``.
2. A batched lookup in ``information_schema.TABLES`` for all candidate table names.
"""

from __future__ import annotations

import pytest

from mariadb_db_agents.common.config import DBConfig
from mariadb_db_agents.common.db_client import (
    _extract_mysql_prefixed_tables,
    _extract_unqualified_table_names,
    _table_exists_in_schema,
    detect_table_database,
)


class _QueuedCursor:
    """Cursor stub: each ``execute`` consumes the next ``fetchall`` / ``fetchone`` result."""

    def __init__(self, fetchall_queue: list | None = None, fetchone_queue: list | None = None):
        self._fetchall_q: list = list(fetchall_queue or [])
        self._fetchone_q: list = list(fetchone_queue or [])
        self.executed: list[tuple[str, tuple | None]] = []

    def execute(self, sql: str, params: tuple | None = None):
        self.executed.append((sql.strip(), params))

    def fetchall(self):
        if not self._fetchall_q:
            raise AssertionError("fetchall called but queue empty")
        return self._fetchall_q.pop(0)

    def fetchone(self):
        if not self._fetchone_q:
            raise AssertionError("fetchone called but queue empty")
        return self._fetchone_q.pop(0)


def _cfg(preferred_db: str = "app") -> DBConfig:
    return DBConfig(
        host="h",
        port=3306,
        user="u",
        password="p",
        database=preferred_db,
    )


def test_detect_no_candidates_when_only_real_mysql_table():
    """Qualified ``mysql.slow_log`` exists in mysql → nothing to resolve."""
    cur = _QueuedCursor(
        fetchall_queue=[[{"TABLE_NAME": "slow_log"}]],
    )
    assert detect_table_database("SELECT * FROM mysql.slow_log LIMIT 1", _cfg(), cur) is None
    assert len(cur.executed) == 1


def test_detect_bogus_mysql_prefix_single_schema():
    cur = _QueuedCursor(
        fetchall_queue=[
            [],  # no such table in mysql
            [{"TABLE_NAME": "mytab", "TABLE_SCHEMA": "app"}],
        ]
    )
    out = detect_table_database(
        "SELECT * FROM mysql.mytab WHERE id = 1",
        _cfg("other"),
        cur,
    )
    assert out == "app"
    assert len(cur.executed) == 2


def test_detect_unqualified_single_table():
    """No mysql refs → only the batched IS query."""
    cur = _QueuedCursor(
        fetchall_queue=[[{"TABLE_NAME": "orders", "TABLE_SCHEMA": "sales"}]],
    )
    assert detect_table_database("SELECT * FROM orders LIMIT 5", _cfg(), cur) == "sales"
    assert len(cur.executed) == 1


def test_detect_join_two_tables_same_schema():
    cur = _QueuedCursor(
        fetchall_queue=[
            [
                {"TABLE_NAME": "a", "TABLE_SCHEMA": "db1"},
                {"TABLE_NAME": "b", "TABLE_SCHEMA": "db1"},
            ]
        ],
    )
    assert (
        detect_table_database("SELECT * FROM a JOIN b ON a.id = b.id", _cfg(), cur) == "db1"
    )


def test_detect_ambiguous_no_preferred_returns_none():
    cur = _QueuedCursor(
        fetchall_queue=[
            [
                {"TABLE_NAME": "t", "TABLE_SCHEMA": "s1"},
                {"TABLE_NAME": "t", "TABLE_SCHEMA": "s2"},
            ]
        ],
    )
    assert detect_table_database("SELECT * FROM t", _cfg("s9"), cur) is None


def test_detect_ambiguous_prefers_cfg_database():
    cur = _QueuedCursor(
        fetchall_queue=[
            [
                {"TABLE_NAME": "t", "TABLE_SCHEMA": "s1"},
                {"TABLE_NAME": "t", "TABLE_SCHEMA": "s2"},
            ]
        ],
    )
    assert detect_table_database("SELECT * FROM t", _cfg("s2"), cur) == "s2"


def test_detect_disjoint_tables_returns_none():
    cur = _QueuedCursor(
        fetchall_queue=[
            [
                {"TABLE_NAME": "a", "TABLE_SCHEMA": "db1"},
                {"TABLE_NAME": "b", "TABLE_SCHEMA": "db2"},
            ]
        ],
    )
    assert detect_table_database("SELECT * FROM a JOIN b", _cfg(), cur) is None


def test_extract_mysql_prefixed_tables():
    assert _extract_mysql_prefixed_tables("FROM mysql.slow_log") == ["slow_log"]


def test_extract_unqualified_skips_dual():
    sql = "SELECT 1 FROM dual"
    names = _extract_unqualified_table_names(sql)
    assert "dual" not in [n.lower() for n in names]


def test_table_exists_in_schema_uses_fetchone():
    cur = _QueuedCursor(fetchone_queue=[{"1": 1}])
    assert _table_exists_in_schema(cur, "mysql", "slow_log") is True
    cur2 = _QueuedCursor(fetchone_queue=[None])
    assert _table_exists_in_schema(cur2, "mysql", "nope") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
