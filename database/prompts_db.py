"""
Optional database storage for prompts (id, name, namespace, content, created_at).

Allows prompts to be edited later via API. For now registry loading from files is sufficient;
this module provides the schema and helpers for future use.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from database.db import db


def _ensure_schema() -> None:
    """Schema from Alembic only; no runtime DDL."""
    return


def upsert_prompt(name: str, namespace: str, content: str) -> Dict[str, Any]:
    """Insert or update a prompt by name. Returns row as dict."""
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    now = datetime.utcnow()
    cur.execute(
        """
        INSERT INTO prompts (name, namespace, content, created_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            namespace = excluded.namespace,
            content = excluded.content
        """,
        (name, namespace, content, now),
    )
    conn.commit()
    cur.execute(
        "SELECT id, name, namespace, content, created_at FROM prompts WHERE name = ?",
        (name,),
    )
    row = cur.fetchone()
    if row is None:
        return {}
    created = row["created_at"]
    if hasattr(created, "isoformat"):
        created = created.isoformat()
    return {
        "id": row["id"],
        "name": row["name"],
        "namespace": row["namespace"],
        "content": row["content"],
        "created_at": created,
    }


def get_prompt_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Return prompt row by name, or None."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        "SELECT id, name, namespace, content, created_at FROM prompts WHERE name = ?",
        (name,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    created = row["created_at"]
    if hasattr(created, "isoformat"):
        created = created.isoformat()
    return {
        "id": row["id"],
        "name": row["name"],
        "namespace": row["namespace"],
        "content": row["content"],
        "created_at": created,
    }


def list_prompts_db(limit: int = 500) -> List[Dict[str, Any]]:
    """List all prompts from DB."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT id, name, namespace, content, created_at
        FROM prompts
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (limit,),
    )
    out = []
    for row in cur.fetchall():
        created = row["created_at"]
        if hasattr(created, "isoformat"):
            created = created.isoformat()
        out.append({
            "id": row["id"],
            "name": row["name"],
            "namespace": row["namespace"],
            "content": row["content"],
            "created_at": created,
        })
    return out
