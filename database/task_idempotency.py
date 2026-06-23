"""
Task idempotency: prevent duplicate execution of the same logical task.

Table: task_idempotency (Alembic `e1f2a3b4c5d6`) — idempotency_key, task_id UUID, status, result.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Dict, Optional, Tuple, Union

from database.db import db


def _ensure_schema() -> None:
    """Schema from Alembic only (`e1f2a3b4c5d6`)."""
    return


def _tid(task_id: Union[str, uuid.UUID]) -> uuid.UUID:
    if isinstance(task_id, uuid.UUID):
        return task_id
    s = str(task_id).strip()
    if s.isdigit():
        raise ValueError("task_id must be a UUID")
    return uuid.UUID(s)


def get_record(idempotency_key: str) -> Optional[Dict[str, Any]]:
    """Return record for key, or None."""
    cur = db.get_connection().cursor()
    cur.execute(
        "SELECT idempotency_key, task_id, status, result, created_at FROM task_idempotency WHERE idempotency_key = ?",
        (idempotency_key,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    return {
        "idempotency_key": row["idempotency_key"],
        "task_id": row["task_id"],
        "status": row["status"],
        "result": row["result"],
        "created_at": row["created_at"],
    }


def try_claim(
    idempotency_key: str, task_id: Union[str, uuid.UUID]
) -> Tuple[bool, Optional[str]]:
    """
    Try to claim execution: insert (key, task_id, status=running).
    Returns (True, None) if claimed; (False, existing_status) if key already exists.
    """
    tid = _tid(task_id)
    conn = db.get_connection()
    cur = conn.cursor()
    now = datetime.utcnow()
    # ON CONFLICT keeps this a single round-trip and (critically) makes pg_compat
    # skip its SELECT lastval() probe — task_idempotency has a non-serial PK, so the
    # probe errors and aborts the transaction, silently dropping the claim row.
    cur.execute(
        """
        INSERT INTO task_idempotency (idempotency_key, task_id, status, result, created_at)
        VALUES (?, ?, 'running', NULL, ?)
        ON CONFLICT (idempotency_key) DO NOTHING
        """,
        (idempotency_key, tid, now),
    )
    if cur.rowcount == 0:
        conn.commit()
        row = get_record(idempotency_key)
        return (False, row["status"] if row else None)
    conn.commit()
    return (True, None)


def set_completed(idempotency_key: str, result: Any = None) -> None:
    """Mark idempotency record as completed and store result."""
    conn = db.get_connection()
    cur = conn.cursor()
    result_str = (
        json.dumps(result)
        if result is not None and not isinstance(result, str)
        else (result if isinstance(result, str) else None)
    )
    cur.execute(
        "UPDATE task_idempotency SET status = 'completed', result = ? WHERE idempotency_key = ?",
        (result_str, idempotency_key),
    )
    conn.commit()


def get_result(idempotency_key: str) -> Optional[Any]:
    """Return stored result for completed key (parsed JSON or string), or None."""
    row = get_record(idempotency_key)
    if row is None or row.get("status") != "completed":
        return None
    raw = row.get("result")
    if raw is None:
        return None
    if isinstance(raw, str) and raw.strip().startswith("{"):
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            pass
    return raw


def delete_record(idempotency_key: str) -> None:
    """Remove record so the same key can be claimed again (e.g. after failure)."""
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM task_idempotency WHERE idempotency_key = ?", (idempotency_key,))
    conn.commit()
