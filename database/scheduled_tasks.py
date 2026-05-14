"""
Scheduled tasks: table and helpers for the scheduler.

Table: scheduled_tasks (id, agent, task_text, cron_expression, enabled, created_at, last_run_at).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from database.db import db


def _ensure_schema() -> None:
    """Schema from Alembic only; no runtime DDL."""
    return


def create(
    agent: Optional[str],
    task_text: str,
    cron_expression: str,
    enabled: bool = True,
    project_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Insert a scheduled task. Returns the created row as a dict."""
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    now = datetime.utcnow()
    cur.execute(
        """
        INSERT INTO scheduled_tasks (agent, task_text, cron_expression, enabled, created_at, project_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (agent, task_text, cron_expression, 1 if enabled else 0, now, project_id),
    )
    conn.commit()
    row_id = int(cur.lastrowid)
    return {
        "id": row_id,
        "agent": agent,
        "task_text": task_text,
        "cron_expression": cron_expression,
        "enabled": enabled,
        "created_at": now.isoformat() if hasattr(now, "isoformat") else str(now),
        "last_run_at": None,
        "project_id": project_id,
    }


def list_all(project_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Return scheduled tasks, optionally filtered by project_id."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    if project_id is not None:
        cur.execute(
            """
            SELECT id, agent, task_text, cron_expression, enabled, created_at, last_run_at, project_id
            FROM scheduled_tasks
            WHERE project_id = ?
            ORDER BY id DESC
            """,
            (project_id,),
        )
    else:
        cur.execute(
            """
            SELECT id, agent, task_text, cron_expression, enabled, created_at, last_run_at, project_id
            FROM scheduled_tasks
            ORDER BY id DESC
            """
        )
    return [_row_to_dict(r) for r in cur.fetchall()]


def list_enabled() -> List[Dict[str, Any]]:
    """Return only enabled scheduled tasks (for the scheduler loop)."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT id, agent, task_text, cron_expression, enabled, created_at, last_run_at, project_id
        FROM scheduled_tasks
        WHERE enabled = 1
        ORDER BY id ASC
        """
    )
    return [_row_to_dict(r) for r in cur.fetchall()]


def get_by_id(schedule_id: int) -> Optional[Dict[str, Any]]:
    """Return a scheduled task by id, or None."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT id, agent, task_text, cron_expression, enabled, created_at, last_run_at, project_id
        FROM scheduled_tasks
        WHERE id = ?
        """,
        (schedule_id,),
    )
    row = cur.fetchone()
    return _row_to_dict(row) if row else None


def set_enabled(schedule_id: int, enabled: bool) -> bool:
    """Set enabled flag. Returns True if a row was updated."""
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE scheduled_tasks SET enabled = ? WHERE id = ?",
        (1 if enabled else 0, schedule_id),
    )
    conn.commit()
    return cur.rowcount > 0


def update_last_run(schedule_id: int, at: datetime) -> None:
    """Update last_run_at for a schedule (after enqueueing)."""
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE scheduled_tasks SET last_run_at = ? WHERE id = ?",
        (at, schedule_id),
    )
    conn.commit()


def _row_to_dict(row: Any) -> Dict[str, Any]:
    created = row["created_at"]
    last_run = row["last_run_at"]
    out = {
        "id": row["id"],
        "agent": row["agent"],
        "task_text": row["task_text"],
        "cron_expression": row["cron_expression"],
        "enabled": bool(row["enabled"]),
        "created_at": created.isoformat() if hasattr(created, "isoformat") else created,
        "last_run_at": last_run.isoformat() if last_run and hasattr(last_run, "isoformat") else last_run,
    }
    if "project_id" in row.keys():
        out["project_id"] = row["project_id"]
    return out
