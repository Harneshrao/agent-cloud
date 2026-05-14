"""
Tracks DAG node execution for distributed workflows.

Table: workflow_nodes (Alembic-managed)
  workflow_id UUID FK tasks(id), node_id, task_id UUID FK tasks(id), ...
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional, Union

from database.db import db


def _ensure_schema() -> None:
    """Schema is created by Alembic (see c4a8b1d2e3f4_legacy_project_workflow_uuid)."""
    return


def _wid(w: Union[uuid.UUID, str]) -> str:
    return str(w)


def insert_nodes(
    workflow_id: Union[uuid.UUID, str], nodes: List[Dict[str, Any]]
) -> None:
    """Insert a row per node. task_id is null; set when task is created and enqueued."""
    _ensure_schema()
    wf = _wid(workflow_id)
    conn = db.get_connection()
    cur = conn.cursor()
    for n in nodes:
        node_id = n.get("id") or ""
        agent_name = n.get("agent") or ""
        deps = n.get("deps")
        if not isinstance(deps, list):
            deps = []
        deps_json = json.dumps(deps)
        task_text = n.get("task") or n.get("task_text") or ""
        cur.execute(
            """
            INSERT INTO workflow_nodes (workflow_id, node_id, task_id, agent_name, deps, task_text, status)
            VALUES (?, ?, NULL, ?, ?, ?, 'pending')
            ON CONFLICT (workflow_id, node_id) DO UPDATE SET
                agent_name = EXCLUDED.agent_name,
                deps = EXCLUDED.deps,
                task_text = EXCLUDED.task_text,
                status = EXCLUDED.status
            """,
            (wf, node_id, agent_name, deps_json, task_text),
        )
    conn.commit()


def get_nodes(workflow_id: Union[uuid.UUID, str]) -> List[Dict[str, Any]]:
    """Return all nodes for the workflow."""
    _ensure_schema()
    wf = _wid(workflow_id)
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT workflow_id, node_id, task_id, agent_name, deps, task_text, status
        FROM workflow_nodes
        WHERE workflow_id = ?
        ORDER BY node_id
        """,
        (wf,),
    )
    out = []
    for row in cur.fetchall():
        deps = row["deps"]
        if isinstance(deps, str):
            try:
                deps = json.loads(deps) if deps.strip() else []
            except (json.JSONDecodeError, TypeError):
                deps = []
        out.append({
            "workflow_id": row["workflow_id"],
            "node_id": row["node_id"],
            "task_id": row["task_id"],
            "agent_name": row["agent_name"],
            "deps": deps,
            "task_text": row.get("task_text") or "",
            "status": row["status"],
        })
    return out


def set_node_task_id(
    workflow_id: Union[uuid.UUID, str],
    node_id: str,
    task_id: Union[uuid.UUID, str],
) -> None:
    """Set task_id for a node when the task is created and enqueued."""
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE workflow_nodes SET task_id = ? WHERE workflow_id = ? AND node_id = ?",
        (_wid(task_id), _wid(workflow_id), node_id),
    )
    conn.commit()


def set_node_status(
    workflow_id: Union[uuid.UUID, str], node_id: str, status: str
) -> None:
    """Update node status (e.g. running, completed, failed)."""
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE workflow_nodes SET status = ? WHERE workflow_id = ? AND node_id = ?",
        (status, _wid(workflow_id), node_id),
    )
    conn.commit()


def get_node_status(
    workflow_id: Union[uuid.UUID, str], node_id: str
) -> Optional[str]:
    """Return status for one node, or None."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        "SELECT status FROM workflow_nodes WHERE workflow_id = ? AND node_id = ?",
        (_wid(workflow_id), node_id),
    )
    row = cur.fetchone()
    return row["status"] if row else None


def get_dependents(
    workflow_id: Union[uuid.UUID, str], completed_node_id: str
) -> List[Dict[str, Any]]:
    """Return nodes that have completed_node_id in their deps (candidates for becoming ready)."""
    nodes = get_nodes(workflow_id)
    return [n for n in nodes if completed_node_id in (n.get("deps") or [])]


def all_nodes_completed(workflow_id: Union[uuid.UUID, str]) -> bool:
    """True if every node has status 'completed' or 'failed'."""
    nodes = get_nodes(workflow_id)
    if not nodes:
        return True
    return all(n.get("status") in ("completed", "failed") for n in nodes)


def get_node_by_task_id(
    task_id: Union[uuid.UUID, str],
) -> Optional[Dict[str, Any]]:
    """Return workflow_nodes row for this task_id, or None."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        "SELECT workflow_id, node_id, task_id, agent_name, deps, task_text, status FROM workflow_nodes WHERE task_id = ?",
        (_wid(task_id),),
    )
    row = cur.fetchone()
    if row is None:
        return None
    deps = row["deps"]
    if isinstance(deps, str):
        try:
            deps = json.loads(deps) if deps.strip() else []
        except (json.JSONDecodeError, TypeError):
            deps = []
    return {
        "workflow_id": row["workflow_id"],
        "node_id": row["node_id"],
        "task_id": row["task_id"],
        "agent_name": row["agent_name"],
        "deps": deps,
        "task_text": row.get("task_text") or "",
        "status": row["status"],
    }
