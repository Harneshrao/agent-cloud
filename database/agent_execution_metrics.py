"""
Agent execution metrics: runtime_ms, memory_used, success per run.
Used for trust scoring and marketplace ranking.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from database.db import db


def _ensure_schema() -> None:
    """Schema from Alembic only; no runtime DDL."""
    return


def record_execution_metric(
    agent_id: Optional[int],
    version: Optional[str],
    task_id: Optional[int],
    runtime_ms: int,
    memory_used: Optional[int],
    success: bool,
) -> None:
    """Record one execution for trust scoring and ranking."""
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    now = datetime.utcnow()
    cur.execute(
        """
        INSERT INTO agent_execution_metrics (agent_id, version, task_id, runtime_ms, memory_used, success, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (agent_id, version or None, task_id, runtime_ms, memory_used, 1 if success else 0, now),
    )
    conn.commit()


def get_metrics_for_agent(agent_id: int, limit: int = 100) -> List[Dict[str, Any]]:
    """Return recent execution metrics for an agent."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT id, agent_id, version, task_id, runtime_ms, memory_used, success, created_at
        FROM agent_execution_metrics
        WHERE agent_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (agent_id, limit),
    )
    rows = cur.fetchall()
    return [
        {
            "id": r["id"],
            "agent_id": r["agent_id"],
            "version": r["version"],
            "task_id": r["task_id"],
            "runtime_ms": r["runtime_ms"],
            "memory_used": r["memory_used"],
            "success": bool(r["success"]),
            "created_at": r["created_at"].isoformat() if hasattr(r["created_at"], "isoformat") else str(r["created_at"]),
        }
        for r in rows
    ]
