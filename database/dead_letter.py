"""
Dead letter queue: tasks that exceeded retry limit are stored for inspection.

Tables:
  dead_letter_tasks (task_id UUID, workflow_id UUID, ...)
  task_retries (task_id UUID, retry_count) — per-task retry count for active tasks

PostgreSQL UUID keys align with tasks.id.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from database.db import db


MAX_RETRIES = 3


def _tid(task_id: Union[uuid.UUID, str]) -> uuid.UUID:
    if isinstance(task_id, uuid.UUID):
        return task_id
    return uuid.UUID(str(task_id))


def _ensure_schema() -> None:
    """Schema from Alembic only (`f8a9b0c1d2e3`)."""
    return


def get_retry_count(task_id: Union[uuid.UUID, str]) -> int:
    """Return current retry count for task_id (0 if never failed)."""
    tid = _tid(task_id)
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute("SELECT retry_count FROM task_retries WHERE task_id = ?", (tid,))
    row = cur.fetchone()
    return int(row["retry_count"]) if row else 0


def increment_retry_count(task_id: Union[uuid.UUID, str]) -> int:
    """Increment retry count for task_id; return new count."""
    tid = _tid(task_id)
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO task_retries (task_id, retry_count)
        VALUES (?, 1)
        ON CONFLICT(task_id) DO UPDATE SET retry_count = task_retries.retry_count + 1
        """,
        (tid,),
    )
    conn.commit()
    cur.execute("SELECT retry_count FROM task_retries WHERE task_id = ?", (tid,))
    row = cur.fetchone()
    return int(row["retry_count"]) if row else 0


def insert_dead_letter(
    task_id: Union[uuid.UUID, str],
    task_payload: str,
    error: str,
    retry_count: int,
    workflow_id: Optional[Union[uuid.UUID, str]] = None,
    node_id: Optional[str] = None,
    agent_name: Optional[str] = None,
) -> None:
    """Store a task in the dead letter queue after it exceeded MAX_RETRIES."""
    tid = _tid(task_id)
    wid = _tid(workflow_id) if workflow_id is not None else None
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    now = datetime.utcnow()
    cur.execute(
        """
        INSERT INTO dead_letter_tasks (task_id, workflow_id, node_id, agent_name, task_payload, error, retry_count, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (tid, wid, node_id, agent_name or None, task_payload, error, retry_count, now),
    )
    conn.commit()


def list_dead_letters(limit: int = 100) -> List[Dict[str, Any]]:
    """Return dead letter tasks, newest first."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT task_id, workflow_id, node_id, agent_name, task_payload, error, retry_count, created_at
        FROM dead_letter_tasks
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (limit,),
    )
    out = []
    for row in cur.fetchall():
        created = row["created_at"]
        if hasattr(created, "isoformat"):
            created = created.isoformat()
        tid = row["task_id"]
        wid = row["workflow_id"]
        out.append({
            "task_id": str(tid) if tid is not None else None,
            "workflow_id": str(wid) if wid is not None else None,
            "node_id": row["node_id"],
            "agent_name": row["agent_name"],
            "task_payload": row["task_payload"],
            "error": row["error"],
            "retry_count": row["retry_count"],
            "created_at": created,
        })
    return out

