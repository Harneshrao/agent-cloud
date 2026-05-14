"""
Scheduled automation for installed agents: cron-based runs.

Table: agent_schedules
  schedule_id, installation_id, cron_expression, status, created_at, last_run_at

Scheduler periodically checks and triggers run_agent(installation_id).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from database.db import db


def _ensure_schema() -> None:
    """Schema from Alembic only; no runtime DDL."""
    return


def create_schedule(installation_id: int, cron_expression: str, status: str = "active") -> int:
    """Create a schedule. Returns schedule_id."""
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    now = datetime.utcnow()
    cur.execute(
        """
        INSERT INTO agent_schedules (installation_id, cron_expression, status, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (installation_id, cron_expression.strip(), status.strip().lower(), now),
    )
    conn.commit()
    return int(cur.lastrowid)


def get_schedule(schedule_id: int) -> Optional[Dict[str, Any]]:
    """Return schedule by id."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT schedule_id, installation_id, cron_expression, status, created_at, last_run_at
        FROM agent_schedules WHERE schedule_id = ?
        """,
        (schedule_id,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    created = row["created_at"]
    last_run = row["last_run_at"]
    if hasattr(created, "isoformat"):
        created = created.isoformat()
    if hasattr(last_run, "isoformat"):
        last_run = last_run.isoformat()
    return {
        "schedule_id": row["schedule_id"],
        "installation_id": row["installation_id"],
        "cron_expression": row["cron_expression"],
        "status": row["status"],
        "created_at": created,
        "last_run_at": last_run,
    }


def list_schedules_by_installation(installation_id: int) -> List[Dict[str, Any]]:
    """List schedules for an installation."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT schedule_id, installation_id, cron_expression, status, created_at, last_run_at
        FROM agent_schedules WHERE installation_id = ?
        ORDER BY created_at DESC
        """,
        (installation_id,),
    )
    return [get_schedule(r["schedule_id"]) for r in cur.fetchall() if get_schedule(r["schedule_id"])]


def list_active_schedules() -> List[Dict[str, Any]]:
    """List all schedules with status = 'active' (for scheduler tick)."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT schedule_id, installation_id, cron_expression, status, created_at, last_run_at
        FROM agent_schedules WHERE status = 'active'
        ORDER BY schedule_id ASC
        """,
    )
    out = []
    for row in cur.fetchall():
        s = get_schedule(row["schedule_id"])
        if s:
            out.append(s)
    return out


def update_schedule_status(schedule_id: int, status: str) -> bool:
    """Set schedule status (e.g. 'active', 'paused'). Returns True if updated."""
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE agent_schedules SET status = ? WHERE schedule_id = ?",
        (status.strip().lower(), schedule_id),
    )
    conn.commit()
    return cur.rowcount > 0


def update_last_run(schedule_id: int, last_run_at: Optional[datetime] = None) -> None:
    """Update last_run_at for a schedule (called after triggering run)."""
    _ensure_schema()
    if last_run_at is None:
        last_run_at = datetime.utcnow()
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE agent_schedules SET last_run_at = ? WHERE schedule_id = ?",
        (last_run_at, schedule_id),
    )
    conn.commit()
