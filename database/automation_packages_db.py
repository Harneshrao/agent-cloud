"""
Metadata table for automation packages available on the platform.

Table: automation_packages
  id, name, version, description, created_at
Optional: sync from package_registry when listing or when loading packages.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from database.db import db


def _ensure_schema() -> None:
    """Schema from Alembic only; no runtime DDL."""
    return


def upsert_package(name: str, version: str, description: str = "") -> Dict[str, Any]:
    """Insert or update package metadata. Returns row as dict."""
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    now = datetime.utcnow()
    cur.execute(
        """
        INSERT INTO automation_packages (name, version, description, created_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(name, version) DO UPDATE SET
            description = excluded.description
        """,
        (name, version, description or "", now),
    )
    conn.commit()
    cur.execute(
        "SELECT id, name, version, description, created_at FROM automation_packages WHERE name = ? AND version = ?",
        (name, version),
    )
    row = cur.fetchone()
    created = row["created_at"]
    if hasattr(created, "isoformat"):
        created = created.isoformat()
    return {
        "id": row["id"],
        "name": row["name"],
        "version": row["version"],
        "description": row["description"] or "",
        "created_at": created,
    }


def list_packages_db(limit: int = 100) -> List[Dict[str, Any]]:
    """List all automation package rows from DB."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT id, name, version, description, created_at
        FROM automation_packages
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
            "version": row["version"],
            "description": row["description"] or "",
            "created_at": created,
        })
    return out
