"""
Agent Marketplace store: persistence for published agents.

Uses the same SQLite database as the rest of the platform (database.db).
Table: agents (id, name, description, version, capabilities, author, price, created_at).
The combination (name, version) is unique; multiple versions of the same agent are allowed.
"""

from __future__ import annotations

import json
import psycopg2
from datetime import datetime
from typing import Any, Dict, List, Optional

from database.db import db
from database.agent_pricing import get_price as get_agent_pricing


def _ensure_schema() -> None:
    """Schema from Alembic only; no runtime DDL."""
    return


def _row_to_agent_dict(row) -> Dict[str, Any]:
    """Turn a DB row into a standard agent dict with capabilities as list and created_at serialized."""
    caps = row["capabilities"]
    if isinstance(caps, str):
        try:
            caps = json.loads(caps)
        except (json.JSONDecodeError, TypeError):
            caps = []
    created = row["created_at"]
    if hasattr(created, "isoformat"):
        created = created.isoformat()
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "version": row["version"],
        "capabilities": caps,
        "author": row["author"],
        "price": row["price"],
        "created_at": created,
    }


def publish_agent(
    name: str,
    description: str,
    version: str,
    capabilities: List[str],
    author: str,
    price: float = 0.0,
) -> Dict[str, Any]:
    """
    Register a new agent version in the marketplace.
    The combination (name, version) must be unique; duplicate (name, version) raises.
    Returns the created row as a dict.
    """
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    capabilities_json = json.dumps(capabilities)
    created_at = datetime.utcnow()
    try:
        cur.execute(
            """
            INSERT INTO agents (name, description, version, capabilities, author, price, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (name, description, version, capabilities_json, author, price, created_at),
        )
        conn.commit()
    except psycopg2.IntegrityError:
        conn.rollback()
        raise ValueError(
            f"Agent with name '{name}' and version '{version}' already exists. "
            "Use a different version to publish."
        )
    row_id = int(cur.lastrowid)
    return {
        "id": row_id,
        "name": name,
        "description": description,
        "version": version,
        "capabilities": capabilities,
        "author": author,
        "price": price,
        "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at),
    }


def get_agent_by_name(name: str) -> Optional[Dict[str, Any]]:
    """
    Return the newest version of the agent with the given name.
    Sorted by created_at descending. Returns None if no agent with that name exists.
    """
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT id, name, description, version, capabilities, author, price, created_at
        FROM agents
        WHERE name = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (name,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    return _row_to_agent_dict(row)


def list_published_agents() -> List[Dict[str, Any]]:
    """
    Return all published agents from the marketplace, ordered by created_at descending.
    Includes price_per_run and currency from agent_pricing (monetization) when set.
    """
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT id, name, description, version, capabilities, author, price, created_at
        FROM agents
        ORDER BY created_at DESC
        """
    )
    rows = cur.fetchall()
    out = [_row_to_agent_dict(row) for row in rows]
    for agent in out:
        pricing = get_agent_pricing(agent["name"])
        agent["price_per_run"] = pricing["price_per_run"] if pricing else None
        agent["currency"] = pricing["currency"] if pricing else "USD"
    return out


# Ensure table exists when module is first imported.
