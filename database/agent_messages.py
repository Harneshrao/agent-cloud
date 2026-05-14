"""
Multi-agent coordination: messages between agent instances.

Table: agent_messages (id, from_agent_instance, to_agent_instance, message_type, payload, status, created_at)
Status: pending | delivered | processed
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from database.db import db


def _ensure_schema() -> None:
    """Schema from Alembic only; no runtime DDL."""
    return


def create_message(
    from_agent_instance: str,
    to_agent_instance: str,
    message_type: str,
    payload: Any = None,
) -> int:
    """Insert a message. Returns the new message id. status = 'pending'."""
    _ensure_schema()
    payload_str = json.dumps(payload) if payload is not None and not isinstance(payload, str) else (payload or "")
    conn = db.get_connection()
    cur = conn.cursor()
    now = datetime.utcnow()
    cur.execute(
        """
        INSERT INTO agent_messages (from_agent_instance, to_agent_instance, message_type, payload, status, created_at)
        VALUES (?, ?, ?, ?, 'pending', ?)
        """,
        (from_agent_instance.strip(), to_agent_instance.strip(), message_type.strip(), payload_str, now),
    )
    conn.commit()
    return int(cur.lastrowid)


def get_pending_for_instance(to_agent_instance: str) -> List[Dict[str, Any]]:
    """Return all messages for to_agent_instance with status = 'pending', ordered by created_at."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT id, from_agent_instance, to_agent_instance, message_type, payload, status, created_at
        FROM agent_messages
        WHERE to_agent_instance = ? AND status = 'pending'
        ORDER BY created_at ASC
        """,
        (to_agent_instance.strip(),),
    )
    return [_row_to_message(r) for r in cur.fetchall()]


def mark_delivered(message_id: int) -> bool:
    """Set status to 'delivered'. Returns True if a row was updated."""
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE agent_messages SET status = 'delivered' WHERE id = ? AND status = 'pending'",
        (message_id,),
    )
    conn.commit()
    return cur.rowcount > 0


def mark_processed(message_id: int) -> bool:
    """Set status to 'processed'. Returns True if a row was updated."""
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE agent_messages SET status = 'processed' WHERE id = ? AND status IN ('pending', 'delivered')",
        (message_id,),
    )
    conn.commit()
    return cur.rowcount > 0


def get_message(message_id: int) -> Optional[Dict[str, Any]]:
    """Return one message by id, or None."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT id, from_agent_instance, to_agent_instance, message_type, payload, status, created_at
        FROM agent_messages
        WHERE id = ?
        """,
        (message_id,),
    )
    row = cur.fetchone()
    return _row_to_message(row) if row else None


def _row_to_message(row: Any) -> Dict[str, Any]:
    payload = row.get("payload")
    if isinstance(payload, str) and payload.strip():
        try:
            payload = json.loads(payload)
        except (json.JSONDecodeError, TypeError):
            pass
    created = row["created_at"]
    if hasattr(created, "isoformat"):
        created = created.isoformat()
    return {
        "id": row["id"],
        "from_agent_instance": row["from_agent_instance"],
        "to_agent_instance": row["to_agent_instance"],
        "message_type": row["message_type"],
        "payload": payload,
        "status": row["status"],
        "created_at": created,
    }
