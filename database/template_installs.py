"""
Template installs: per-project installed templates with optional config.

Table: template_installs
  id, template_id, project_id, config_json (TEXT), installed_at
  UNIQUE(template_id, project_id)
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from database.db import db


def _ensure_schema() -> None:
    """Schema from Alembic only; no runtime DDL."""
    return


def _row_to_install(row) -> Dict[str, Any]:
    at = row["installed_at"]
    if hasattr(at, "isoformat"):
        at = at.isoformat()
    cfg = row.get("config_json")
    if isinstance(cfg, str):
        try:
            cfg = json.loads(cfg) if cfg.strip() else {}
        except (json.JSONDecodeError, TypeError):
            cfg = {}
    if cfg is not None and not isinstance(cfg, dict):
        cfg = {}
    return {
        "id": row["id"],
        "template_id": row["template_id"],
        "project_id": row["project_id"],
        "config_json": cfg or {},
        "installed_at": at,
    }


def install(
    template_id: int,
    project_id: int,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Install a template for a project. Idempotent: replaces existing install (same template_id, project_id)."""
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    config_json = json.dumps(config) if config and isinstance(config, dict) else "{}"
    now = datetime.utcnow()
    cur.execute(
        """
        INSERT INTO template_installs (template_id, project_id, config_json, installed_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(template_id, project_id) DO UPDATE SET
            config_json = excluded.config_json,
            installed_at = excluded.installed_at
        """,
        (template_id, project_id, config_json, now),
    )
    conn.commit()
    return get_install(template_id, project_id)


def get_install(template_id: int, project_id: int) -> Optional[Dict[str, Any]]:
    """Return the install row for (template_id, project_id), or None."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT id, template_id, project_id, config_json, installed_at
        FROM template_installs
        WHERE template_id = ? AND project_id = ?
        """,
        (template_id, project_id),
    )
    row = cur.fetchone()
    if row is None:
        return None
    return _row_to_install(row)


def list_installs_for_project(project_id: int, limit: int = 100) -> List[Dict[str, Any]]:
    """Return all template installs for a project."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT id, template_id, project_id, config_json, installed_at
        FROM template_installs
        WHERE project_id = ?
        ORDER BY installed_at DESC
        LIMIT ?
        """,
        (project_id, limit),
    )
    return [_row_to_install(r) for r in cur.fetchall()]


def delete_install(template_id: int, project_id: int) -> bool:
    """Remove install for (template_id, project_id). Returns True if a row was deleted."""
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM template_installs WHERE template_id = ? AND project_id = ?",
        (template_id, project_id),
    )
    conn.commit()
    return cur.rowcount > 0
