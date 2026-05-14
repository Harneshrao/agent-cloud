"""
Event triggers: table and helpers for event-driven workflow start.

Table: event_triggers (id, event_type, agent, task_template, enabled, project_id, source, created_at).
source: 'user' | 'agent' | 'any' — only match events from that source (any = both).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from database.db import db
from database.pg_compat import pg_errors


def _ensure_schema() -> None:
    """Schema from Alembic only; no runtime DDL."""
    return


def create(
    event_type: str,
    task_template: str,
    agent: Optional[str] = None,
    enabled: bool = True,
    project_id: Optional[uuid.UUID] = None,
    source: str = "any",
) -> Dict[str, Any]:
    """Insert an event trigger. source: 'user' | 'agent' | 'any'. Returns the created row as a dict."""
    _ensure_schema()
    src = (source or "any").strip().lower()
    if src not in ("user", "agent", "any"):
        src = "any"
    conn = db.get_connection()
    cur = conn.cursor()
    now = datetime.utcnow()
    cur.execute(
        """
        INSERT INTO event_triggers (event_type, agent, task_template, enabled, project_id, source, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (event_type, agent, task_template, 1 if enabled else 0, project_id, src, now),
    )
    conn.commit()
    row_id = int(cur.lastrowid)
    return {
        "id": row_id,
        "event_type": event_type,
        "agent": agent,
        "task_template": task_template,
        "enabled": enabled,
        "project_id": project_id,
        "source": src,
        "created_at": now.isoformat() if hasattr(now, "isoformat") else str(now),
    }


def list_enabled_by_event_type(
    event_type: str,
    project_id: Optional[uuid.UUID] = None,
    source: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return enabled triggers that match event_type, optional project_id and source ('user'|'agent'|'any')."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    sql = """
        SELECT id, event_type, agent, task_template, enabled, created_at, project_id, source
        FROM event_triggers
        WHERE event_type = ? AND enabled = 1
        """
    params: List[Any] = [event_type]
    if project_id is not None:
        sql += " AND (project_id IS NULL OR project_id = ?)"
        params.append(project_id)
    if source and str(source).strip().lower() in ("user", "agent"):
        sql += " AND (source IS NULL OR source = ? OR source = 'any')"
        params.append(str(source).strip().lower())
    sql += " ORDER BY id ASC"
    cur.execute(sql, params)
    return [_row_to_dict(r) for r in cur.fetchall()]


def list_all(project_id: Optional[uuid.UUID] = None) -> List[Dict[str, Any]]:
    """Return all event triggers, optionally filtered by project_id."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    if project_id is not None:
        cur.execute(
            """
            SELECT id, event_type, agent, task_template, enabled, created_at, project_id, source
            FROM event_triggers
            WHERE project_id IS NULL OR project_id = ?
            ORDER BY id DESC
            """,
            (project_id,),
        )
    else:
        cur.execute(
            """
            SELECT id, event_type, agent, task_template, enabled, created_at, project_id, source
            FROM event_triggers
            ORDER BY id DESC
            """
        )
    return [_row_to_dict(r) for r in cur.fetchall()]


def get_by_id(trigger_id: int) -> Optional[Dict[str, Any]]:
    """Return a trigger by id, or None."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT id, event_type, agent, task_template, enabled, created_at, project_id, source
        FROM event_triggers
        WHERE id = ?
        """,
        (trigger_id,),
    )
    row = cur.fetchone()
    return _row_to_dict(row) if row else None


def set_enabled(trigger_id: int, enabled: bool) -> bool:
    """Set enabled flag. Returns True if a row was updated."""
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE event_triggers SET enabled = ? WHERE id = ?",
        (1 if enabled else 0, trigger_id),
    )
    conn.commit()
    return cur.rowcount > 0


def _row_to_dict(row: Any) -> Dict[str, Any]:
    created = row["created_at"]
    out = {
        "id": row["id"],
        "event_type": row["event_type"],
        "agent": row["agent"],
        "task_template": row["task_template"],
        "enabled": bool(row["enabled"]),
        "created_at": created.isoformat() if hasattr(created, "isoformat") else created,
    }
    if "project_id" in row.keys():
        out["project_id"] = row["project_id"]
    if "source" in row.keys():
        out["source"] = row.get("source") or "any"
    return out
