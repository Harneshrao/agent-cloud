"""
Execution results for user-installed agents: run history and output.

Table: agent_run_results
  run_id, installation_id, task_id, status, output (JSON/text), execution_time_ms, created_at

Written when a task started via run_agent(installation_id) finishes.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from database.db import db


def _ensure_schema() -> None:
    """Schema is created by Alembic (task_id UUID)."""
    return


def _tid(task_id: Union[uuid.UUID, str]) -> str:
    return str(task_id)


def record_run(
    installation_id: int,
    task_id: Union[uuid.UUID, str],
    status: str,
    execution_time_ms: int = 0,
    output: Optional[Any] = None,
) -> int:
    """Insert a run result (called when task completes or fails). Returns run_id."""
    _ensure_schema()
    output_str = json.dumps(output) if output is not None and not isinstance(output, str) else (output if output is not None else None)
    conn = db.get_connection()
    cur = conn.cursor()
    now = datetime.utcnow()
    cur.execute(
        """
        INSERT INTO agent_run_results (installation_id, task_id, status, output, execution_time_ms, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (installation_id, _tid(task_id), status, output_str, execution_time_ms, now),
    )
    conn.commit()
    return int(cur.lastrowid)


def update_output(task_id: Union[uuid.UUID, str], output: Any) -> bool:
    """Update the output for a run result by task_id. Returns True if updated."""
    _ensure_schema()
    output_str = json.dumps(output) if output is not None and not isinstance(output, str) else (output if output is not None else None)
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE agent_run_results SET output = ? WHERE task_id = ?",
        (output_str, _tid(task_id)),
    )
    conn.commit()
    return cur.rowcount > 0


def list_runs_by_installation(
    installation_id: int,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """List run results for an installation, newest first."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT run_id, installation_id, task_id, status, output, execution_time_ms, created_at
        FROM agent_run_results
        WHERE installation_id = ?
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
        """,
        (installation_id, limit, offset),
    )
    out = []
    for row in cur.fetchall():
        o = row["output"]
        if isinstance(o, str) and o:
            try:
                o = json.loads(o)
            except (json.JSONDecodeError, TypeError):
                pass
        created = row["created_at"]
        if hasattr(created, "isoformat"):
            created = created.isoformat()
        out.append({
            "run_id": row["run_id"],
            "installation_id": row["installation_id"],
            "task_id": row["task_id"],
            "status": row["status"],
            "output": o,
            "execution_time_ms": row["execution_time_ms"] or 0,
            "created_at": created,
        })
    return out


def get_run_by_task_id(task_id: Union[uuid.UUID, str]) -> Optional[Dict[str, Any]]:
    """Return run result by task_id, or None."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT run_id, installation_id, task_id, status, output, execution_time_ms, created_at
        FROM agent_run_results WHERE task_id = ?
        """,
        (_tid(task_id),),
    )
    row = cur.fetchone()
    if row is None:
        return None
    o = row["output"]
    if isinstance(o, str) and o:
        try:
            o = json.loads(o)
        except (json.JSONDecodeError, TypeError):
            pass
    created = row["created_at"]
    if hasattr(created, "isoformat"):
        created = created.isoformat()
    return {
        "run_id": row["run_id"],
        "installation_id": row["installation_id"],
        "task_id": row["task_id"],
        "status": row["status"],
        "output": o,
        "execution_time_ms": row["execution_time_ms"] or 0,
        "created_at": created,
    }
