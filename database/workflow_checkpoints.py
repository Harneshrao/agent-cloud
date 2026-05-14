"""
Workflow checkpointing: persist node status and result for recovery.

Table: workflow_checkpoints — Alembic-managed; workflow_id UUID FK tasks(id).
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from database.db import db


def _ensure_schema() -> None:
    """Schema is created by Alembic."""
    return


def _wid(w: Union[uuid.UUID, str]) -> str:
    return str(w)


def initialize_workflow(
    workflow_id: Union[uuid.UUID, str], node_ids: List[str]
) -> None:
    """Create checkpoint rows for all nodes with status=pending. Call when workflow starts."""
    _ensure_schema()
    wf = _wid(workflow_id)
    conn = db.get_connection()
    cur = conn.cursor()
    now = datetime.utcnow()
    for node_id in node_ids:
        cur.execute(
            """
            INSERT INTO workflow_checkpoints (workflow_id, node_id, status, result, updated_at)
            VALUES (?, ?, 'pending', NULL, ?)
            ON CONFLICT (workflow_id, node_id) DO UPDATE SET
                status = EXCLUDED.status,
                result = EXCLUDED.result,
                updated_at = EXCLUDED.updated_at
            """,
            (wf, node_id, now),
        )
    conn.commit()


def get_checkpoint(
    workflow_id: Union[uuid.UUID, str], node_id: str
) -> Optional[Dict[str, Any]]:
    """Return checkpoint row for (workflow_id, node_id), or None."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT workflow_id, node_id, status, result, updated_at
        FROM workflow_checkpoints
        WHERE workflow_id = ? AND node_id = ?
        """,
        (_wid(workflow_id), node_id),
    )
    row = cur.fetchone()
    if row is None:
        return None
    return _row_to_checkpoint(row)


def _row_to_checkpoint(row: Any) -> Dict[str, Any]:
    updated = row["updated_at"]
    if hasattr(updated, "isoformat"):
        updated = updated.isoformat()
    result = row.get("result")
    if isinstance(result, str) and result.strip().startswith("{"):
        try:
            result = json.loads(result)
        except (json.JSONDecodeError, TypeError):
            pass
    return {
        "workflow_id": row["workflow_id"],
        "node_id": row["node_id"],
        "status": row["status"],
        "result": result,
        "updated_at": updated,
    }


def get_all_checkpoints(
    workflow_id: Union[uuid.UUID, str],
) -> List[Dict[str, Any]]:
    """Return all checkpoint rows for the workflow."""
    _ensure_schema()
    wf = _wid(workflow_id)
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT workflow_id, node_id, status, result, updated_at
        FROM workflow_checkpoints
        WHERE workflow_id = ?
        ORDER BY node_id
        """,
        (wf,),
    )
    return [_row_to_checkpoint(r) for r in cur.fetchall()]


def set_checkpoint(
    workflow_id: Union[uuid.UUID, str],
    node_id: str,
    status: str,
    result: Any = None,
) -> None:
    """Set checkpoint status and optionally result. status: pending | running | completed | failed."""
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    now = datetime.utcnow()
    result_str = (
        json.dumps(result)
        if result is not None and not isinstance(result, str)
        else (result if isinstance(result, str) else None)
    )
    cur.execute(
        """
        INSERT INTO workflow_checkpoints (workflow_id, node_id, status, result, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(workflow_id, node_id) DO UPDATE SET
            status = excluded.status,
            result = excluded.result,
            updated_at = excluded.updated_at
        """,
        (_wid(workflow_id), node_id, status, result_str or None, now),
    )
    conn.commit()


def set_running(workflow_id: Union[uuid.UUID, str], node_id: str) -> None:
    """Mark node as running (worker started execution)."""
    set_checkpoint(workflow_id, node_id, "running")


def set_completed(
    workflow_id: Union[uuid.UUID, str], node_id: str, result: Any = None
) -> None:
    """Mark node completed and store result."""
    set_checkpoint(workflow_id, node_id, "completed", result=result)


def set_failed(workflow_id: Union[uuid.UUID, str], node_id: str) -> None:
    """Mark node failed (DAG scheduler may retry)."""
    set_checkpoint(workflow_id, node_id, "failed")


def checkpoint_status(
    workflow_id: Union[uuid.UUID, str], node_id: str
) -> Optional[str]:
    """Return checkpoint status for the node, or None."""
    cp = get_checkpoint(workflow_id, node_id)
    return cp["status"] if cp else None
