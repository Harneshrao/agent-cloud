"""
Worker capability registry: which workers advertise which capabilities.

Table: worker_capabilities (worker_id, capability).
Workers register capabilities at startup for resource-aware scheduling.
"""

from __future__ import annotations

from typing import List

from database.db import db


def _ensure_schema() -> None:
    """Schema from Alembic only; no runtime DDL."""
    return


def set_capabilities(worker_id: str, capabilities: List[str]) -> None:
    """
    Set the full set of capabilities for a worker. Replaces any existing.
    Call at worker startup to advertise capabilities (e.g. python, gpu, browser).
    """
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM worker_capabilities WHERE worker_id = ?", (worker_id,))
    for cap in capabilities:
        cap = (cap or "").strip()
        if not cap:
            continue
        cur.execute(
            """
            INSERT INTO worker_capabilities (worker_id, capability) VALUES (?, ?)
            ON CONFLICT DO NOTHING
            """,
            (worker_id, cap),
        )
    conn.commit()


def get_capabilities(worker_id: str) -> List[str]:
    """Return the list of capabilities advertised by the worker."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        "SELECT capability FROM worker_capabilities WHERE worker_id = ? ORDER BY capability",
        (worker_id,),
    )
    return [row["capability"] for row in cur.fetchall()]
