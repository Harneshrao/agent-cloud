"""
Agent Simulation Environment: sandbox for testing agent teams and workflows.

Tables:
  simulation_runs: id, project_id, scenario_name, status, created_at, metrics
  simulation_events: simulation_id, event_type, payload, created_at (injected events)
  simulation_agent_instances, simulation_knowledge_graph, simulation_knowledge_edges,
  simulation_agent_memory: clones of production data keyed by simulation_id
  simulation_tasks: tasks created during simulation (isolated from production queue)
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from database.db import db


def _ensure_schema() -> None:
    """Schema from Alembic only; no runtime DDL."""
    return


def create_simulation(project_id: int, scenario_name: str) -> int:
    """Create a new simulation run. status = 'created'. Returns simulation id."""
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    now = datetime.utcnow()
    cur.execute(
        """
        INSERT INTO simulation_runs (project_id, scenario_name, status, created_at)
        VALUES (?, ?, 'created', ?)
        """,
        (project_id, (scenario_name or "").strip(), now),
    )
    conn.commit()
    return int(cur.lastrowid)


def list_simulations_for_project(project_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    """Return simulations for a project, newest first."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT id, project_id, scenario_name, status, created_at,
               tasks_created, workflows_executed, messages_sent,
               tasks_completed, tasks_failed
        FROM simulation_runs WHERE project_id = ?
        ORDER BY created_at DESC LIMIT ?
        """,
        (project_id, limit),
    )
    return [_row_to_simulation_run(r) for r in cur.fetchall() or []]


def get_simulation(simulation_id: int) -> Optional[Dict[str, Any]]:
    """Return simulation run by id."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT id, project_id, scenario_name, status, created_at,
               tasks_created, workflows_executed, messages_sent,
               tasks_completed, tasks_failed
        FROM simulation_runs WHERE id = ?
        """,
        (simulation_id,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    return _row_to_simulation_run(row)


def _row_to_simulation_run(row: Any) -> Dict[str, Any]:
    created = row["created_at"]
    if hasattr(created, "isoformat"):
        created = created.isoformat()
    total = max(1, (row["tasks_completed"] or 0) + (row["tasks_failed"] or 0))
    success_rate = (row["tasks_completed"] or 0) / total if total else 0.0
    return {
        "id": row["id"],
        "project_id": row["project_id"],
        "scenario_name": row["scenario_name"],
        "status": row["status"],
        "created_at": created,
        "tasks_created": row["tasks_created"] or 0,
        "workflows_executed": row["workflows_executed"] or 0,
        "messages_sent": row["messages_sent"] or 0,
        "tasks_completed": row["tasks_completed"] or 0,
        "tasks_failed": row["tasks_failed"] or 0,
        "success_rate": round(success_rate, 4),
    }


def start_simulation(simulation_id: int) -> bool:
    """
    Start a simulation: clone agent_instances, knowledge_graph, agent_memory for the run's project
    into simulation context, then set status to 'running'.
    """
    run = get_simulation(simulation_id)
    if run is None:
        return False
    if run["status"] not in ("created", "stopped"):
        return False
    clone_project_state_into_simulation(simulation_id, run["project_id"])
    return set_simulation_status(simulation_id, "running")


def set_simulation_status(simulation_id: int, status: str) -> bool:
    """Set simulation status (e.g. 'running', 'completed', 'stopped')."""
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE simulation_runs SET status = ? WHERE id = ?",
        (status.strip().lower(), simulation_id),
    )
    conn.commit()
    return cur.rowcount > 0


def update_simulation_metrics(
    simulation_id: int,
    tasks_created: Optional[int] = None,
    workflows_executed: Optional[int] = None,
    messages_sent: Optional[int] = None,
    tasks_completed: Optional[int] = None,
    tasks_failed: Optional[int] = None,
) -> bool:
    """Increment or set simulation metrics. Pass only fields to update."""
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    updates = []
    params: List[Any] = []
    if tasks_created is not None:
        updates.append("tasks_created = tasks_created + ?")
        params.append(tasks_created)
    if workflows_executed is not None:
        updates.append("workflows_executed = workflows_executed + ?")
        params.append(workflows_executed)
    if messages_sent is not None:
        updates.append("messages_sent = messages_sent + ?")
        params.append(messages_sent)
    if tasks_completed is not None:
        updates.append("tasks_completed = tasks_completed + ?")
        params.append(tasks_completed)
    if tasks_failed is not None:
        updates.append("tasks_failed = tasks_failed + ?")
        params.append(tasks_failed)
    if not updates:
        return True
    params.append(simulation_id)
    cur.execute(
        f"UPDATE simulation_runs SET {', '.join(updates)} WHERE id = ?",
        params,
    )
    conn.commit()
    return cur.rowcount > 0


# --- Simulation events (injection) ---


def inject_event(
    simulation_id: int,
    event_type: str,
    payload: Optional[Dict[str, Any]] = None,
) -> int:
    """Append an event to the simulation. Agents react via normal event triggers. Returns event id."""
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    payload_str = json.dumps(payload) if payload is not None else None
    now = datetime.utcnow()
    cur.execute(
        """
        INSERT INTO simulation_events (simulation_id, event_type, payload, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (simulation_id, (event_type or "").strip(), payload_str, now),
    )
    conn.commit()
    return int(cur.lastrowid)


def list_simulation_events(simulation_id: int) -> List[Dict[str, Any]]:
    """Return all events for a simulation, oldest first."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT id, simulation_id, event_type, payload, created_at
        FROM simulation_events WHERE simulation_id = ?
        ORDER BY created_at ASC
        """,
        (simulation_id,),
    )
    out = []
    for row in cur.fetchall() or []:
        p = row["payload"]
        if isinstance(p, str) and p:
            try:
                p = json.loads(p)
            except (json.JSONDecodeError, TypeError):
                pass
        created = row["created_at"]
        if hasattr(created, "isoformat"):
            created = created.isoformat()
        out.append({
            "id": row["id"],
            "simulation_id": row["simulation_id"],
            "event_type": row["event_type"],
            "payload": p,
            "created_at": created,
        })
    return out


# --- Clone state into simulation ---


def clone_project_state_into_simulation(simulation_id: int, project_id: int) -> None:
    """
    Clone agent_instances, knowledge_graph (entities + edges), and agent_memory
    for the project into simulation-scoped tables. Clears any existing clone data for this run first.
    """
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM simulation_agent_instances WHERE simulation_id = ?", (simulation_id,))
    cur.execute("DELETE FROM simulation_knowledge_graph WHERE simulation_id = ?", (simulation_id,))
    cur.execute("DELETE FROM simulation_knowledge_edges WHERE simulation_id = ?", (simulation_id,))
    cur.execute("DELETE FROM simulation_agent_memory WHERE simulation_id = ?", (simulation_id,))

    # Agent instances
    cur.execute(
        """
        INSERT INTO simulation_agent_instances
          (simulation_id, id, agent_name, project_id, role, state, created_at)
        SELECT ?, id, agent_name, project_id, role, state, created_at
        FROM agent_instances WHERE project_id = ?
        ON CONFLICT (simulation_id, id) DO UPDATE SET
            agent_name = EXCLUDED.agent_name,
            project_id = EXCLUDED.project_id,
            role = EXCLUDED.role,
            state = EXCLUDED.state,
            created_at = EXCLUDED.created_at
        """,
        (simulation_id, project_id),
    )

    # Knowledge graph entities
    cur.execute(
        """
        INSERT INTO simulation_knowledge_graph
          (simulation_id, entity_id, entity_type, data, project_id, created_at)
        SELECT ?, entity_id, entity_type, data, project_id, created_at
        FROM knowledge_graph WHERE project_id = ?
        """,
        (simulation_id, project_id),
    )

    # Knowledge edges
    cur.execute(
        """
        INSERT INTO simulation_knowledge_edges
          (simulation_id, source_entity, target_entity, relationship, project_id)
        SELECT ?, source_entity, target_entity, relationship, project_id
        FROM knowledge_edges WHERE project_id = ?
        """,
        (simulation_id, project_id),
    )

    # Agent memory (all rows for project)
    cur.execute(
        """
        INSERT INTO simulation_agent_memory
          (simulation_id, agent_name, project_id, key, value, created_at)
        SELECT ?, agent_name, project_id, key, value, created_at
        FROM agent_memory WHERE project_id = ?
        """,
        (simulation_id, project_id),
    )

    conn.commit()


# --- Simulation context: read/write clone tables ---


def get_simulation_instances(simulation_id: int) -> List[Dict[str, Any]]:
    """Return agent instances for this simulation (from clone)."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT id, agent_name, project_id, role, state, created_at
        FROM simulation_agent_instances WHERE simulation_id = ?
        ORDER BY created_at ASC
        """,
        (simulation_id,),
    )
    return [_row_to_sim_instance(r) for r in cur.fetchall() or []]


def _row_to_sim_instance(row: Any) -> Dict[str, Any]:
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


def list_instances_for_project_simulation(
    simulation_id: int,
    project_id: int,
    agent_name: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """List instances from simulation clone, optionally by agent_name."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    if agent_name:
        cur.execute(
            """
            SELECT id, agent_name, project_id, role, state, created_at
            FROM simulation_agent_instances
            WHERE simulation_id = ? AND project_id = ? AND agent_name = ?
            ORDER BY created_at DESC LIMIT ?
            """,
            (simulation_id, project_id, agent_name, limit),
        )
    else:
        cur.execute(
            """
            SELECT id, agent_name, project_id, role, state, created_at
            FROM simulation_agent_instances
            WHERE simulation_id = ? AND project_id = ?
            ORDER BY created_at DESC LIMIT ?
            """,
            (simulation_id, project_id, limit),
        )
    return [_row_to_sim_instance(r) for r in cur.fetchall() or []]


def get_instance_simulation(simulation_id: int, instance_id: str) -> Optional[Dict[str, Any]]:
    """Get one agent instance from simulation clone by instance id."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT id, agent_name, project_id, role, state, created_at
        FROM simulation_agent_instances
        WHERE simulation_id = ? AND id = ?
        """,
        (simulation_id, instance_id.strip()),
    )
    row = cur.fetchone()
    if row is None:
        return None
    return _row_to_sim_instance(row)


def update_instance_state_simulation(
    simulation_id: int,
    instance_id: str,
    state: Dict[str, Any],
) -> bool:
    """Update instance state in simulation clone."""
    _ensure_schema()
    state_json = json.dumps(state) if state else "{}"
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE simulation_agent_instances SET state = ?
        WHERE simulation_id = ? AND id = ?
        """,
        (state_json, simulation_id, instance_id.strip()),
    )
    conn.commit()
    return cur.rowcount > 0


def _memory_key_simulation(key: str, agent_instance_id: Optional[str]) -> str:
    if agent_instance_id and str(agent_instance_id).strip():
        return str(agent_instance_id).strip() + ":" + key
    return key


def store_memory_simulation(
    simulation_id: int,
    agent_name: str,
    project_id: int,
    key: str,
    value: Any,
    agent_instance_id: Optional[str] = None,
) -> None:
    """Store memory in simulation_agent_memory (clone)."""
    _ensure_schema()
    if not isinstance(value, str):
        value = json.dumps(value)
    stored_key = _memory_key_simulation(key, agent_instance_id)
    conn = db.get_connection()
    cur = conn.cursor()
    now = datetime.utcnow()
    cur.execute(
        """
        INSERT INTO simulation_agent_memory (simulation_id, agent_name, project_id, key, value, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(simulation_id, agent_name, project_id, key)
        DO UPDATE SET value = excluded.value, created_at = excluded.created_at
        """,
        (simulation_id, agent_name.strip(), project_id, stored_key, value, now),
    )
    conn.commit()


def retrieve_memory_simulation(
    simulation_id: int,
    agent_name: str,
    project_id: int,
    key: str,
    agent_instance_id: Optional[str] = None,
) -> Optional[str]:
    """Retrieve memory from simulation_agent_memory (clone)."""
    _ensure_schema()
    stored_key = _memory_key_simulation(key, agent_instance_id)
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT value FROM simulation_agent_memory
        WHERE simulation_id = ? AND agent_name = ? AND project_id = ? AND key = ?
        """,
        (simulation_id, agent_name.strip(), project_id, stored_key),
    )
    row = cur.fetchone()
    return row["value"] if row else None


def search_memory_simulation(
    simulation_id: int,
    agent_name: str,
    project_id: int,
    agent_instance_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return all memory entries from simulation clone (key, value, created_at)."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    if agent_instance_id and str(agent_instance_id).strip():
        prefix = str(agent_instance_id).strip() + ":"
        cur.execute(
            """
            SELECT key, value, created_at FROM simulation_agent_memory
            WHERE simulation_id = ? AND agent_name = ? AND project_id = ? AND key LIKE ?
            ORDER BY created_at DESC
            """,
            (simulation_id, agent_name.strip(), project_id, prefix + "%"),
        )
        rows = cur.fetchall() or []
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
        SELECT key, value, created_at FROM simulation_agent_memory
        WHERE simulation_id = ? AND agent_name = ? AND project_id = ?
        ORDER BY created_at DESC
        """,
        (simulation_id, agent_name.strip(), project_id),
    )
    rows = cur.fetchall() or []
    return [
        {"key": row["key"], "value": row["value"], "created_at": row["created_at"]}
        for row in rows
    ]


def get_entity_simulation(
    simulation_id: int,
    entity_id: str,
    project_id: int,
) -> Optional[Dict[str, Any]]:
    """Get entity from simulation_knowledge_graph (clone)."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT entity_id, entity_type, data, project_id, created_at
        FROM simulation_knowledge_graph
        WHERE simulation_id = ? AND entity_id = ? AND project_id = ?
        """,
        (simulation_id, entity_id.strip(), project_id),
    )
    row = cur.fetchone()
    if row is None:
        return None
    data = row["data"]
    if isinstance(data, str) and data:
        try:
            data = json.loads(data)
        except (json.JSONDecodeError, TypeError):
            pass
    created = row["created_at"]
    if hasattr(created, "isoformat"):
        created = created.isoformat()
    return {
        "entity_id": row["entity_id"],
        "entity_type": row["entity_type"],
        "data": data,
        "project_id": row["project_id"],
        "created_at": created,
    }


def upsert_entity_simulation(
    simulation_id: int,
    entity_id: str,
    entity_type: str,
    data: Dict[str, Any] | str,
    project_id: int,
) -> None:
    """Upsert entity in simulation_knowledge_graph (clone)."""
    _ensure_schema()
    data_str = json.dumps(data) if isinstance(data, dict) else (data if isinstance(data, str) else json.dumps(data))
    conn = db.get_connection()
    cur = conn.cursor()
    now = datetime.utcnow()
    cur.execute(
        """
        INSERT INTO simulation_knowledge_graph (simulation_id, entity_id, entity_type, data, project_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(simulation_id, entity_id, project_id) DO UPDATE SET
            entity_type = excluded.entity_type,
            data = excluded.data
        """,
        (simulation_id, entity_id.strip(), entity_type.strip(), data_str, project_id, now),
    )
    conn.commit()


def add_edge_simulation(
    simulation_id: int,
    source_entity: str,
    target_entity: str,
    relationship: str,
    project_id: int,
) -> None:
    """Add edge in simulation_knowledge_edges (clone)."""
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO simulation_knowledge_edges (simulation_id, source_entity, target_entity, relationship, project_id)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(simulation_id, source_entity, target_entity, relationship, project_id) DO NOTHING
        """,
        (simulation_id, source_entity.strip(), target_entity.strip(), relationship.strip(), project_id),
    )
    conn.commit()


def find_related_entities_simulation(
    simulation_id: int,
    entity_id: str,
    project_id: int,
    relationship: Optional[str] = None,
    direction: str = "outgoing",
) -> List[Dict[str, Any]]:
    """Find related entities in simulation clone."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    entity_id = entity_id.strip()
    out: List[Dict[str, Any]] = []
    if direction in ("outgoing", "both"):
        sql = """
            SELECT target_entity AS related_id, relationship
            FROM simulation_knowledge_edges
            WHERE simulation_id = ? AND source_entity = ? AND project_id = ?
            """
        params: List[Any] = [simulation_id, entity_id, project_id]
        if relationship:
            sql += " AND relationship = ?"
            params.append(relationship.strip())
        cur.execute(sql, params)
        for row in cur.fetchall() or []:
            rec = {"related_entity_id": row["related_id"], "relationship": row["relationship"], "direction": "outgoing"}
            ent = get_entity_simulation(simulation_id, row["related_id"], project_id)
            if ent:
                rec["entity"] = ent
            out.append(rec)
    if direction in ("incoming", "both"):
        sql = """
            SELECT source_entity AS related_id, relationship
            FROM simulation_knowledge_edges
            WHERE simulation_id = ? AND target_entity = ? AND project_id = ?
            """
        params = [simulation_id, entity_id, project_id]
        if relationship:
            sql += " AND relationship = ?"
            params.append(relationship.strip())
        cur.execute(sql, params)
        for row in cur.fetchall() or []:
            rec = {"related_entity_id": row["related_id"], "relationship": row["relationship"], "direction": "incoming"}
            ent = get_entity_simulation(simulation_id, row["related_id"], project_id)
            if ent:
                rec["entity"] = ent
            out.append(rec)
    return out


def list_entities_simulation(
    simulation_id: int,
    project_id: int,
    entity_type: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """List entities from simulation clone."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    if entity_type:
        cur.execute(
            """
            SELECT entity_id, entity_type, data, project_id, created_at
            FROM simulation_knowledge_graph
            WHERE simulation_id = ? AND project_id = ? AND entity_type = ?
            ORDER BY created_at DESC LIMIT ?
            """,
            (simulation_id, project_id, entity_type.strip(), limit),
        )
    else:
        cur.execute(
            """
            SELECT entity_id, entity_type, data, project_id, created_at
            FROM simulation_knowledge_graph
            WHERE simulation_id = ? AND project_id = ?
            ORDER BY created_at DESC LIMIT ?
            """,
            (simulation_id, project_id, limit),
        )
    rows = cur.fetchall() or []
    result = []
    for row in rows:
        data = row["data"]
        if isinstance(data, str) and data:
            try:
                data = json.loads(data)
            except (json.JSONDecodeError, TypeError):
                pass
        created = row["created_at"]
        if hasattr(created, "isoformat"):
            created = created.isoformat()
        result.append({
            "entity_id": row["entity_id"],
            "entity_type": row["entity_type"],
            "data": data,
            "project_id": row["project_id"],
            "created_at": created,
        })
    return result


# --- Simulation tasks (isolated queue) ---


def enqueue_simulation_task(
    simulation_id: int,
    task_text: str,
    status: str = "pending",
) -> int:
    """Enqueue a task for this simulation only. Returns simulation task id. Updates tasks_created."""
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    now = datetime.utcnow()
    cur.execute(
        """
        INSERT INTO simulation_tasks (simulation_id, task_text, status, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (simulation_id, task_text, status, now),
    )
    task_id = int(cur.lastrowid)
    cur.execute(
        "UPDATE simulation_runs SET tasks_created = tasks_created + 1 WHERE id = ?",
        (simulation_id,),
    )
    conn.commit()
    return task_id


def fetch_next_simulation_task(simulation_id: int) -> Optional[Dict[str, Any]]:
    """
    Fetch and claim the next pending simulation task (status -> 'running').
    Reads from simulation_tasks. Returns task dict or None if no pending task.
    """
    return get_next_simulation_task(simulation_id)


def get_next_simulation_task(simulation_id: int) -> Optional[Dict[str, Any]]:
    """Claim next pending simulation task (set status to 'running') and return it."""
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, simulation_id, task_text, status, created_at
        FROM simulation_tasks
        WHERE simulation_id = ? AND status = 'pending'
        ORDER BY created_at ASC LIMIT 1
        """,
        (simulation_id,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    task_id = row["id"]
    cur.execute(
        "UPDATE simulation_tasks SET status = 'running' WHERE id = ?",
        (task_id,),
    )
    conn.commit()
    from services.task_payload import parse_payload as _parse_payload
    parsed = _parse_payload(row["task_text"])
    created = row["created_at"]
    if hasattr(created, "isoformat"):
        created = created.isoformat()
    out = {
        "id": row["id"],
        "simulation_id": row["simulation_id"],
        "task": parsed.get("task", ""),
        "agent": parsed.get("agent"),
        "status": "running",
        "created_at": created,
        "task_text": row["task_text"],
    }
    for k in ("workflow_id", "node_id", "deps", "agent_instance_id"):
        if k in parsed:
            out[k] = parsed[k]
    return out


def complete_simulation_task(simulation_id: int, task_id: int, success: bool) -> None:
    """Mark a simulation task completed or failed. Updates metrics."""
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    status = "completed" if success else "failed"
    cur.execute(
        "UPDATE simulation_tasks SET status = ? WHERE id = ? AND simulation_id = ?",
        (status, task_id, simulation_id),
    )
    if cur.rowcount:
        col = "tasks_completed" if success else "tasks_failed"
        cur.execute(
            f"UPDATE simulation_runs SET {col} = {col} + 1 WHERE id = ?",
            (simulation_id,),
        )
    conn.commit()


# --- Process injected events (drive triggers in sim context) ---


def process_simulation_events(simulation_id: int, project_id: int) -> List[int]:
    """
    For each event in simulation_events for this run, call event engine so triggers
    fire and tasks are enqueued to simulation_tasks (not production).
    Returns list of simulation task ids created.
    """
    from database.event_triggers import list_enabled_by_event_type
    from engine.event_engine import _render_template

    events = list_simulation_events(simulation_id)
    task_ids: List[int] = []
    for ev in events:
        event_type = ev.get("event_type") or ""
        payload = ev.get("payload") or {}
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except (json.JSONDecodeError, TypeError):
                payload = {}
        triggers = list_enabled_by_event_type(event_type, project_id=project_id, source="any")
        for t in triggers:
            task_text = _render_template(t.get("task_template") or "", payload)
            if not task_text:
                continue
            agent = t.get("agent")
            if agent:
                payload_str = json.dumps({"task": task_text, "agent": agent})
            else:
                payload_str = task_text
            tid = enqueue_simulation_task(simulation_id, payload_str)
            task_ids.append(tid)
    return task_ids
