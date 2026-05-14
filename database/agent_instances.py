"""
Persistent agent identity: long-lived AI agents with roles and state.

Table: agent_instances (id, agent_name, project_id, role, state, created_at)
Organizations create instances (e.g. AI Researcher, AI Sales Assistant) that
maintain memory and execute workflows over time.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from database.db import db


def _ensure_schema() -> None:
    """Schema from Alembic only; no runtime DDL."""
    return


def create_instance(
    agent_name: str,
    project_id: int,
    role: Optional[str] = None,
    state: Optional[Dict[str, Any]] = None,
    instance_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a new agent instance. Returns the instance row as dict.
    instance_id: optional; if not provided, generated as inst_<uuid8>.
    """
    _ensure_schema()
    id_ = (instance_id or "inst_" + uuid.uuid4().hex[:12]).strip()
    if not id_:
        id_ = "inst_" + uuid.uuid4().hex[:12]
    state_json = json.dumps(state) if state is not None else None
    conn = db.get_connection()
    cur = conn.cursor()
    now = datetime.utcnow()
    cur.execute(
        """
        INSERT INTO agent_instances (id, agent_name, project_id, role, state, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (id_, agent_name, project_id, role or None, state_json, now),
    )
    conn.commit()
    return get_instance(id_)


def get_instance(instance_id: str, simulation_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Return the agent instance by id, or None. When simulation_id is set, read from simulation clone."""
    if simulation_id is not None:
        from database.simulation import get_instance_simulation
        return get_instance_simulation(simulation_id, instance_id)
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT id, agent_name, project_id, role, state, created_at
        FROM agent_instances
        WHERE id = ?
        """,
        (instance_id.strip(),),
    )
    row = cur.fetchone()
    if row is None:
        return None
    return _row_to_instance(row)


def _row_to_instance(row: Any) -> Dict[str, Any]:
    state = row.get("state")
    if isinstance(state, str) and state:
        try:
            state = json.loads(state)
        except (json.JSONDecodeError, TypeError):
            state = {}
    elif state is None:
        state = {}
    created = row["created_at"]
    if hasattr(created, "isoformat"):
        created = created.isoformat()
    return {
        "id": row["id"],
        "agent_name": row["agent_name"],
        "project_id": row["project_id"],
        "role": row.get("role"),
        "state": state,
        "created_at": created,
    }


def update_state(
    instance_id: str,
    state: Dict[str, Any],
    simulation_id: Optional[int] = None,
) -> bool:
    """Update the state for an instance. When simulation_id is set, update simulation clone only."""
    if simulation_id is not None:
        from database.simulation import update_instance_state_simulation
        return update_instance_state_simulation(simulation_id, instance_id, state)
    _ensure_schema()
    if get_instance(instance_id) is None:
        return False
    state_json = json.dumps(state) if state else "{}"
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE agent_instances SET state = ? WHERE id = ?",
        (state_json, instance_id.strip()),
    )
    conn.commit()
    return cur.rowcount > 0


def list_instances_for_project(
    project_id: int,
    agent_name: Optional[str] = None,
    limit: int = 100,
    simulation_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """List agent instances for a project. When simulation_id is set, read from simulation clone."""
    if simulation_id is not None:
        from database.simulation import list_instances_for_project_simulation
        return list_instances_for_project_simulation(simulation_id, project_id, agent_name, limit)
    _ensure_schema()
    cur = db.get_connection().cursor()
    if agent_name:
        cur.execute(
            """
            SELECT id, agent_name, project_id, role, state, created_at
            FROM agent_instances
            WHERE project_id = ? AND agent_name = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (project_id, agent_name, limit),
        )
    else:
        cur.execute(
            """
            SELECT id, agent_name, project_id, role, state, created_at
            FROM agent_instances
            WHERE project_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (project_id, limit),
        )
    return [_row_to_instance(r) for r in cur.fetchall()]
