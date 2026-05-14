"""
Task Graph: tracks parent-child relationships between tasks.

Table: task_graph (task_id, parent_task_id, status, retry_count, created_at).
Each subtask creates a row linking it to its parent.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from database.db import db


def _graph_legacy_int_id(task_id: Union[int, str, uuid.UUID]) -> Optional[int]:
    """task_graph still uses INTEGER ids; UUID tasks skip graph linkage until migrated."""
    if isinstance(task_id, int):
        return task_id
    s = str(task_id).strip()
    if s.isdigit():
        return int(s)
    return None


def _ensure_schema() -> None:
    """Schema from Alembic only; no runtime DDL."""
    return


def insert_link(
    task_id: int,
    parent_task_id: int,
    status: str = "pending",
    retry_count: int = 0,
) -> None:
    """
    Record a parent-child relationship. Called when a subtask is enqueued.
    """
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO task_graph (task_id, parent_task_id, status, retry_count, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (task_id, parent_task_id, status, retry_count, datetime.utcnow()),
    )
    conn.commit()


def get_row(task_id: int) -> Optional[Dict[str, Any]]:
    """Return the task_graph row for task_id, or None."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        "SELECT task_id, parent_task_id, status, retry_count, created_at FROM task_graph WHERE task_id = ?",
        (task_id,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    return dict(row)


def get_children(parent_task_id: int) -> List[Dict[str, Any]]:
    """Return all task_graph rows where parent_task_id = parent_task_id."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT task_id, parent_task_id, status, retry_count, created_at
        FROM task_graph
        WHERE parent_task_id = ?
        """,
        (parent_task_id,),
    )
    return [dict(r) for r in cur.fetchall()]


def increment_retry_count(task_id: int) -> int:
    """Increment retry_count for task_id; return new value."""
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE task_graph SET retry_count = COALESCE(retry_count, 0) + 1 WHERE task_id = ?",
        (task_id,),
    )
    conn.commit()
    cur.execute("SELECT retry_count FROM task_graph WHERE task_id = ?", (task_id,))
    row = cur.fetchone()
    return int(row["retry_count"]) if row is not None else 0


def update_status(task_id: int, status: str) -> None:
    """
    Update the status of a task in the task graph (e.g. when a task finishes).
    """
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE task_graph SET status = ? WHERE task_id = ?",
        (status, task_id),
    )
    conn.commit()


def get_task_text_and_status(
    task_id: Union[int, str, uuid.UUID],
) -> Optional[Dict[str, Any]]:
    """Return task_text (JSON string from input_json), status, and project_id, or None."""
    tid = str(task_id).strip() if not isinstance(task_id, uuid.UUID) else str(task_id)
    cur = db.get_connection().cursor()
    cur.execute(
        "SELECT id, input_json, status, project_id FROM tasks WHERE id = ?",
        (tid,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    ij = row.get("input_json")
    if isinstance(ij, dict):
        task_text = json.dumps(ij)
    elif ij is None:
        task_text = "{}"
    else:
        task_text = str(ij)
    st = row["status"]
    if hasattr(st, "value"):
        st = st.value
    out = {"task_id": row["id"], "task_text": task_text, "status": st}
    if "project_id" in row.keys():
        out["project_id"] = row["project_id"]
    return out


def get_workflow_view(task_id: Union[int, str, uuid.UUID]) -> Optional[Dict[str, Any]]:
    """
    Return workflow observability data for task_id: task text, status, parent_task_id,
    retry_count, and list of child tasks (each with task_id, task_text, status, retry_count).
    Returns None if the task does not exist in the tasks table.
    """
    task_row = get_task_text_and_status(task_id)
    if task_row is None:
        return None
    gid = _graph_legacy_int_id(task_id)
    graph_row = get_row(gid) if gid is not None else None
    if graph_row is not None:
        status = graph_row.get("status")
        parent_task_id = graph_row.get("parent_task_id")
        retry_count = int(graph_row.get("retry_count") or 0)
    else:
        # Root task: not in task_graph; use status from tasks table.
        status = task_row.get("status")
        parent_task_id = None
        retry_count = 0
    child_rows = get_children(gid) if gid is not None else []
    child_tasks = []
    for c in child_rows:
        ct = get_task_text_and_status(c["task_id"])
        task_text = ct["task_text"] if ct else None
        child_tasks.append({
            "task_id": c["task_id"],
            "task_text": task_text,
            "status": c.get("status"),
            "retry_count": int(c.get("retry_count") or 0),
        })
    root_id = task_row.get("task_id")
    out = {
        "task_id": root_id,
        "task_text": task_row.get("task_text"),
        "status": status,
        "parent_task_id": parent_task_id,
        "retry_count": retry_count,
        "child_tasks": child_tasks,
    }
    if task_row.get("project_id") is not None:
        out["project_id"] = task_row["project_id"]
    return out


# Ensure table exists when module is first imported.
