"""
Agent installs: which projects have used (installed) which agents.

Table: agent_installs (agent_name, project_id, installed_at)
Unique on (agent_name, project_id). Record install on first run per project.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from database.db import db


def _ensure_schema() -> None:
    """Schema from Alembic only; no runtime DDL."""
    return


def record_install(agent_name: str, project_id: int) -> bool:
    """Record that a project has installed (used) an agent. Idempotent. Returns True if inserted."""
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO agent_installs (agent_name, project_id, installed_at)
        VALUES (?, ?, ?)
        ON CONFLICT (agent_name, project_id) DO NOTHING
        """,
        (agent_name, project_id, datetime.utcnow()),
    )
    conn.commit()
    return cur.rowcount > 0


def count_projects_using_agent(agent_name: str) -> int:
    """Return number of distinct projects that have installed this agent."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        "SELECT COUNT(*) AS n FROM agent_installs WHERE agent_name = ?",
        (agent_name,),
    )
    row = cur.fetchone()
    return int(row["n"]) if row else 0


def get_projects_using_agent(agent_name: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Return list of project_ids (and installed_at) for this agent."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT agent_name, project_id, installed_at
        FROM agent_installs
        WHERE agent_name = ?
        ORDER BY installed_at DESC
        LIMIT ?
        """,
        (agent_name, limit),
    )
    out = []
    for row in cur.fetchall():
        at = row["installed_at"]
        if hasattr(at, "isoformat"):
            at = at.isoformat()
        out.append({
            "agent_name": row["agent_name"],
            "project_id": row["project_id"],
            "installed_at": at,
        })
    return out
