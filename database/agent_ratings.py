"""
Agent ratings and reviews. Per-project, per-agent.

Table: agent_ratings (id, agent_name, project_id, rating, review, created_at)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from database.db import db
from database.pg_compat import pg_errors


def _ensure_schema() -> None:
    """Schema from Alembic only; no runtime DDL."""
    return


def add_rating(
    agent_name: str,
    project_id: int,
    rating: int,
    review: Optional[str] = None,
    user_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Insert a rating. Rating 1-5. Returns the created row as dict."""
    _ensure_schema()
    if not (1 <= rating <= 5):
        raise ValueError("rating must be between 1 and 5")
    conn = db.get_connection()
    cur = conn.cursor()
    created_at = datetime.utcnow()
    cur.execute(
        """
        INSERT INTO agent_ratings (agent_name, user_id, project_id, rating, review, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (agent_name, user_id, project_id, rating, review or "", created_at),
    )
    conn.commit()
    row_id = int(cur.lastrowid)
    return {
        "id": row_id,
        "agent_name": agent_name,
        "user_id": user_id,
        "project_id": project_id,
        "rating": rating,
        "review": review or "",
        "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at),
    }


def get_ratings_for_agent(agent_name: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Return ratings for an agent, newest first."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT id, agent_name, user_id, project_id, rating, review, created_at
        FROM agent_ratings
        WHERE agent_name = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (agent_name, limit),
    )
    out = []
    for row in cur.fetchall():
        created = row["created_at"]
        if hasattr(created, "isoformat"):
            created = created.isoformat()
        out.append({
            "id": row["id"],
            "agent_name": row["agent_name"],
            "user_id": row.get("user_id"),
            "project_id": row["project_id"],
            "rating": row["rating"],
            "review": row["review"] or "",
            "created_at": created,
        })
    return out


def get_average_rating_for_agent(agent_name: str) -> Optional[float]:
    """Return average rating for the agent, or None if no ratings."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        "SELECT AVG(rating) AS avg_rating FROM agent_ratings WHERE agent_name = ?",
        (agent_name,),
    )
    row = cur.fetchone()
    if row is None or row["avg_rating"] is None:
        return None
    return round(float(row["avg_rating"]), 2)
