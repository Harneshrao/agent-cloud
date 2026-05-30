"""
PostgreSQL connection with SQLite-ish cursor behavior:
- `?` placeholders → psycopg2 `%s`
- RealDict rows (dict-like, keyed by column name)
- `lastrowid` after INSERT via SELECT lastval()
"""

from __future__ import annotations

import re
from typing import Any, Optional

import psycopg2
from psycopg2 import errors as pg_errors
from psycopg2.extras import RealDictCursor


def _adapt_sql(sql: str) -> str:
    """Translate common SQLite datetime expressions to PostgreSQL."""
    s = sql
    # datetime('now') → UTC now
    s = re.sub(r"datetime\s*\(\s*'now'\s*\)", "NOW() AT TIME ZONE 'UTC'", s, flags=re.I)
    # datetime('now', '-N seconds') style in SQL string (literal, not param)
    s = re.sub(
        r"datetime\s*\(\s*'now'\s*,\s*'([^']+)'\s*\)",
        r"NOW() AT TIME ZONE 'UTC' + INTERVAL '\1'",
        s,
        flags=re.I,
    )
    return s


class CompatCursor:
    def __init__(self, raw_conn) -> None:
        self._raw_conn = raw_conn
        self._cur = raw_conn.cursor(cursor_factory=RealDictCursor)
        self._lastrowid: Optional[int] = None

    def execute(self, sql: str, params: Any = None):
        self._lastrowid = None
        sql = _adapt_sql(sql)
        sql = sql.replace("?", "%s")
        try:
            if params is not None:
                self._cur.execute(sql, params)
            else:
                self._cur.execute(sql)
        except Exception:
            self._raw_conn.rollback()
            raise
        stripped = sql.strip().upper()
        if (
            stripped.startswith("INSERT")
            and "RETURNING" not in stripped
            and "ON CONFLICT" not in stripped
        ):
            try:
                self._cur.execute("SELECT lastval() AS lastval")
                row = self._cur.fetchone()
                if row is not None:
                    self._lastrowid = int(row["lastval"] if isinstance(row, dict) else row[0])
            except Exception:
                # Tables with non-serial PKs (e.g. task_idempotency) — no lastval
                self._lastrowid = None
        return self

    @property
    def lastrowid(self) -> Optional[int]:
        return self._lastrowid

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    @property
    def rowcount(self) -> int:
        return self._cur.rowcount

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._cur.close()


class CompatConnection:
    """psycopg2 connection with SQLite-compatible cursor()."""

    def __init__(self, raw_conn) -> None:
        self._raw = raw_conn

    def cursor(self):
        return CompatCursor(self._raw)

    def commit(self) -> None:
        self._raw.commit()

    def rollback(self) -> None:
        self._raw.rollback()

    def close(self) -> None:
        self._raw.close()


def connect(database_url: str) -> CompatConnection:
    raw = psycopg2.connect(database_url)
    raw.autocommit = False
    return CompatConnection(raw)


__all__ = ["CompatConnection", "CompatCursor", "connect", "pg_errors"]
