"""
Worker registry persistence for observability.

Uses the same PostgreSQL database as the rest of the platform (database.db).
Table: workers (worker_id, last_seen, tasks_running, status).
Workers register on startup and send heartbeats periodically.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from database.db import db


def _ensure_schema() -> None:
    """Schema from Alembic only; no runtime DDL."""
    return


def register_worker(worker_id: str, region: str | None = None, worker_type: str | None = None) -> None:
    """
    Register a worker on startup. Inserts or replaces the worker row with
    initial status 'active', tasks_running 0, current last_seen, optional region and worker_type (e.g. 'edge').
    """
    _ensure_schema()
    now = datetime.utcnow()
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO workers (worker_id, last_seen, tasks_running, status, region, worker_type)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(worker_id) DO UPDATE SET
            last_seen = excluded.last_seen,
            tasks_running = excluded.tasks_running,
            status = excluded.status,
            region = COALESCE(excluded.region, workers.region),
            worker_type = COALESCE(excluded.worker_type, workers.worker_type)
        """,
        (worker_id, now, 0, "active", region, (worker_type.strip().lower() if worker_type and str(worker_type).strip() else None)),
    )
    conn.commit()


def heartbeat(worker_id: str, tasks_running: int = 0, region: str | None = None, worker_type: str | None = None) -> None:
    """
    Update worker heartbeat: last_seen and tasks_running.
    If the worker is not yet registered, registers it first.
    Optional region and worker_type update stored values when provided.
    """
    _ensure_schema()
    now = datetime.utcnow()
    wt = (worker_type.strip().lower() if worker_type and str(worker_type).strip() else None)
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO workers (worker_id, last_seen, tasks_running, status, region, worker_type)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(worker_id) DO UPDATE SET
            last_seen = excluded.last_seen,
            tasks_running = excluded.tasks_running,
            status = 'active',
            region = COALESCE(excluded.region, workers.region),
            worker_type = COALESCE(excluded.worker_type, workers.worker_type)
        """,
        (worker_id, now, tasks_running, "active", region, wt),
    )
    conn.commit()


def get_worker_region(worker_id: str) -> str | None:
    """Return the region for a worker, or None if not set."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute("SELECT region FROM workers WHERE worker_id = ?", (worker_id,))
    row = cur.fetchone()
    return (row["region"] if "region" in row.keys() else None) if row else None


def get_worker_type(worker_id: str) -> str | None:
    """Return the worker_type for a worker (e.g. 'edge'), or None if not set."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute("SELECT worker_type FROM workers WHERE worker_id = ?", (worker_id,))
    row = cur.fetchone()
    return (row["worker_type"] if "worker_type" in row.keys() else None) if row else None


def get_all_workers() -> List[Dict[str, Any]]:
    """Return all workers with worker_id, last_seen, tasks_running, status, region."""
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT worker_id, last_seen, tasks_running, status, region, worker_type
        FROM workers
        ORDER BY last_seen DESC
        """
    )
    rows = cur.fetchall()
    out = []
    for row in rows:
        last_seen = row["last_seen"] if "last_seen" in row.keys() else None
        if last_seen is not None and hasattr(last_seen, "isoformat"):
            last_seen = last_seen.isoformat()
        else:
            last_seen = str(last_seen) if last_seen is not None else None
        out.append({
            "worker_id": row["worker_id"] if "worker_id" in row.keys() else None,
            "region": row["region"] if "region" in row.keys() else None,
            "last_seen": last_seen,
            "tasks_running": (row["tasks_running"] if "tasks_running" in row.keys() else None) or 0,
            "status": (row["status"] if "status" in row.keys() else None) or "unknown",
            "worker_type": row["worker_type"] if "worker_type" in row.keys() else None,
        })
    return out


def count_active_workers(within_seconds: int = 30) -> int:
    """
    Count workers that have sent a heartbeat within the last `within_seconds`.
    """
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*) AS n FROM workers
        WHERE last_seen >= NOW() AT TIME ZONE 'UTC' - (?::interval)
        """,
        (f"{within_seconds} seconds",),
    )
    row = cur.fetchone()
    return row["n"] if row else 0
