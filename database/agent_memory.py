"""
Persistent agent memory: per-agent, per-project key-value store.

Table: agent_memory (agent_name, project_id, key, value, created_at)
Agents can store and retrieve memory across tasks and workflows.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from database.db import db


# Sentinel for "no project" so we can use a simple UNIQUE(agent_name, project_id, key)
_NO_PROJECT = -1


def _ensure_schema() -> None:
    """Schema from Alembic only; no runtime DDL."""
    return


def _memory_key(key: str, agent_instance_id: Optional[str]) -> str:
    """When agent_instance_id is set, prefix key so instance memory is isolated."""
    if agent_instance_id and str(agent_instance_id).strip():
        return str(agent_instance_id).strip() + ":" + key
    return key


def store_memory(
    agent_name: str,
    project_id: Optional[int],
    key: str,
    value: Any,
    agent_instance_id: Optional[str] = None,
    simulation_id: Optional[int] = None,
) -> None:
    """
    Store or overwrite a memory entry for (agent_name, project_id, key).
    When agent_instance_id is set, key is stored with prefix so instance memory is isolated.
    When simulation_id is set, writes to simulation_agent_memory (clone) only.
    value is serialized as string (e.g. JSON); pass dict/list for automatic JSON.
    """
    if simulation_id is not None and project_id is not None:
        from database.simulation import store_memory_simulation
        store_memory_simulation(simulation_id, agent_name, project_id, key, value, agent_instance_id)
        return
    _ensure_schema()
    if not isinstance(value, str):
        import json
        value = json.dumps(value)
    stored_key = _memory_key(key, agent_instance_id)
    conn = db.get_connection()
    cur = conn.cursor()
    now = datetime.utcnow()
    proj = _NO_PROJECT if project_id is None else project_id
    cur.execute(
        """
        INSERT INTO agent_memory (agent_name, project_id, key, value, created_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(agent_name, project_id, key)
        DO UPDATE SET value = excluded.value, created_at = excluded.created_at
        """,
        (agent_name, proj, stored_key, value, now),
    )
    conn.commit()


def retrieve_memory(
    agent_name: str,
    project_id: Optional[int],
    key: str,
    agent_instance_id: Optional[str] = None,
    simulation_id: Optional[int] = None,
) -> Optional[str]:
    """
    Return the value for (agent_name, project_id, key), or None if not found.
    When agent_instance_id is set, key is looked up with instance prefix.
    When simulation_id is set, reads from simulation_agent_memory (clone) only.
    """
    if simulation_id is not None and project_id is not None:
        from database.simulation import retrieve_memory_simulation
        return retrieve_memory_simulation(simulation_id, agent_name, project_id, key, agent_instance_id)
    _ensure_schema()
    stored_key = _memory_key(key, agent_instance_id)
    proj = _NO_PROJECT if project_id is None else project_id
    cur = db.get_connection().cursor()
    cur.execute(
        "SELECT value FROM agent_memory WHERE agent_name = ? AND project_id = ? AND key = ?",
        (agent_name, proj, stored_key),
    )
    row = cur.fetchone()
    if row is None:
        return None
    return row["value"]


def search_memory(
    agent_name: str,
    project_id: Optional[int],
    agent_instance_id: Optional[str] = None,
    simulation_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Return all memory entries for (agent_name, project_id). When simulation_id is set, use simulation clone.
    """
    if simulation_id is not None and project_id is not None:
        from database.simulation import search_memory_simulation
        return search_memory_simulation(simulation_id, agent_name, project_id, agent_instance_id)
    _ensure_schema()
    proj = _NO_PROJECT if project_id is None else project_id
    cur = db.get_connection().cursor()
    if agent_instance_id and str(agent_instance_id).strip():
        prefix = str(agent_instance_id).strip() + ":"
        cur.execute(
            """
            SELECT key, value, created_at FROM agent_memory
            WHERE agent_name = ? AND project_id = ? AND key LIKE ?
            ORDER BY created_at DESC
            """,
            (agent_name, proj, prefix + "%"),
        )
        rows = cur.fetchall()
        return [
            {
                "key": (row["key"][len(prefix):] if row["key"].startswith(prefix) else row["key"]),
                "value": row["value"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]
    cur.execute(
        """
        SELECT key, value, created_at FROM agent_memory
        WHERE agent_name = ? AND project_id = ?
        ORDER BY created_at DESC
        """,
        (agent_name, proj),
    )
    rows = cur.fetchall()
    return [
        {"key": row["key"], "value": row["value"], "created_at": row["created_at"]}
        for row in rows
    ]
