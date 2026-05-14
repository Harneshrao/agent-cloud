"""
Package install stats for marketplace ranking (trending packages).

Table: package_stats (package_name PRIMARY KEY, install_count, last_installed_at)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from database.db import db


def _ensure_schema() -> None:
    """Schema from Alembic only; no runtime DDL."""
    return


def increment_package_install(package_name: str) -> None:
    """Record one install; increment install_count and set last_installed_at."""
    if not package_name or not str(package_name).strip():
        return
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    now = datetime.utcnow()
    cur.execute(
        """
        INSERT INTO package_stats (package_name, install_count, last_installed_at)
        VALUES (?, 1, ?)
        ON CONFLICT(package_name) DO UPDATE SET
            install_count = install_count + 1,
            last_installed_at = excluded.last_installed_at
        """,
        (package_name.strip(), now),
    )
    conn.commit()


def get_all_package_stats() -> List[Dict[str, Any]]:
    """Return all package_stats rows for ranking."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT package_name, install_count, last_installed_at
        FROM package_stats
        ORDER BY install_count DESC, last_installed_at DESC
        """
    )
    out = []
    for row in cur.fetchall():
        last = row["last_installed_at"]
        if last is not None and hasattr(last, "isoformat"):
            last = last.isoformat()
        out.append({
            "package_name": row["package_name"],
            "install_count": int(row["install_count"]),
            "last_installed_at": last,
        })
    return out
