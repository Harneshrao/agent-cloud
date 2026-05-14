"""
Organization knowledge graph: shared entities and relations across agents.

Tables:
  knowledge_graph: entity_id, entity_type, data (JSON), project_id, created_at
  knowledge_edges: source_entity, target_entity, relationship, project_id

Agents use get_entity() and find_related_entities() to collaborate on company data,
market insights, customer information, etc.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from database.db import db


def _ensure_schema() -> None:
    """Schema from Alembic only; no runtime DDL."""
    return


def upsert_entity(
    entity_id: str,
    entity_type: str,
    data: Dict[str, Any] | str,
    project_id: int,
    simulation_id: Optional[int] = None,
) -> None:
    """Insert or update an entity in the knowledge graph. When simulation_id is set, use simulation clone."""
    if simulation_id is not None:
        from database.simulation import upsert_entity_simulation
        upsert_entity_simulation(simulation_id, entity_id, entity_type, data, project_id)
        return
    _ensure_schema()
    data_str = json.dumps(data) if isinstance(data, dict) else (data if isinstance(data, str) else json.dumps(data))
    conn = db.get_connection()
    cur = conn.cursor()
    now = datetime.utcnow()
    cur.execute(
        """
        INSERT INTO knowledge_graph (entity_id, entity_type, data, project_id, created_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(entity_id, project_id) DO UPDATE SET
            entity_type = excluded.entity_type,
            data = excluded.data
        """,
        (entity_id.strip(), entity_type.strip(), data_str, project_id, now),
    )
    conn.commit()


def get_entity(
    entity_id: str,
    project_id: int,
    simulation_id: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """
    Return the entity by entity_id and project_id, or None.
    When simulation_id is set, reads from simulation clone.
    Returns dict with entity_id, entity_type, data (parsed JSON), project_id, created_at.
    """
    if simulation_id is not None:
        from database.simulation import get_entity_simulation
        return get_entity_simulation(simulation_id, entity_id, project_id)
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT entity_id, entity_type, data, project_id, created_at
        FROM knowledge_graph
        WHERE entity_id = ? AND project_id = ?
        """,
        (entity_id.strip(), project_id),
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


def add_edge(
    source_entity: str,
    target_entity: str,
    relationship: str,
    project_id: int,
    simulation_id: Optional[int] = None,
) -> None:
    """Add a directed edge. When simulation_id is set, use simulation clone."""
    if simulation_id is not None:
        from database.simulation import add_edge_simulation
        add_edge_simulation(simulation_id, source_entity, target_entity, relationship, project_id)
        return
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO knowledge_edges (source_entity, target_entity, relationship, project_id)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(source_entity, target_entity, relationship, project_id) DO NOTHING
        """,
        (source_entity.strip(), target_entity.strip(), relationship.strip(), project_id),
    )
    conn.commit()


def find_related_entities(
    entity_id: str,
    project_id: int,
    relationship: Optional[str] = None,
    direction: str = "outgoing",
) -> List[Dict[str, Any]]:
    """
    Find entities related to entity_id by edges in this project.
    relationship: optional filter by relationship type.
    direction: "outgoing" (source_entity = entity_id), "incoming" (target_entity = entity_id), or "both".
    Returns list of { target_entity, relationship } for outgoing, { source_entity, relationship } for incoming,
    or both; each includes the related entity's data when available via get_entity.
    """
    _ensure_schema()
    cur = db.get_connection().cursor()
    entity_id = entity_id.strip()
    out: List[Dict[str, Any]] = []
    if direction in ("outgoing", "both"):
        sql = """
            SELECT target_entity AS related_id, relationship
            FROM knowledge_edges
            WHERE source_entity = ? AND project_id = ?
            """
        params: List[Any] = [entity_id, project_id]
        if relationship:
            sql += " AND relationship = ?"
            params.append(relationship.strip())
        cur.execute(sql, params)
        for row in cur.fetchall() or []:
            rec = {"related_entity_id": row["related_id"], "relationship": row["relationship"], "direction": "outgoing"}
            ent = get_entity(row["related_id"], project_id)
            if ent:
                rec["entity"] = ent
            out.append(rec)
    if direction in ("incoming", "both"):
        sql = """
            SELECT source_entity AS related_id, relationship
            FROM knowledge_edges
            WHERE target_entity = ? AND project_id = ?
            """
        params = [entity_id, project_id]
        if relationship:
            sql += " AND relationship = ?"
            params.append(relationship.strip())
        cur.execute(sql, params)
        for row in cur.fetchall() or []:
            rec = {"related_entity_id": row["related_id"], "relationship": row["relationship"], "direction": "incoming"}
            ent = get_entity(row["related_id"], project_id)
            if ent:
                rec["entity"] = ent
            out.append(rec)
    return out


def list_entities(
    project_id: int,
    entity_type: Optional[str] = None,
    limit: int = 100,
    simulation_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """List entities in the project. When simulation_id is set, uses simulation clone."""
    if simulation_id is not None:
        from database.simulation import list_entities_simulation
        return list_entities_simulation(simulation_id, project_id, entity_type, limit)
    _ensure_schema()
    cur = db.get_connection().cursor()
    if entity_type:
        cur.execute(
            """
            SELECT entity_id, entity_type, data, project_id, created_at
            FROM knowledge_graph
            WHERE project_id = ? AND entity_type = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (project_id, entity_type.strip(), limit),
        )
    else:
        cur.execute(
            """
            SELECT entity_id, entity_type, data, project_id, created_at
            FROM knowledge_graph
            WHERE project_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (project_id, limit),
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
