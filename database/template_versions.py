"""
Versioned workflow template DAGs.

Table: workflow_template_versions
  id, template_id, version, dag_definition (JSON text), created_at
Each template may have multiple versions; version is a string (e.g. "1.0", "v2").
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from database.db import db


def _ensure_schema() -> None:
    """Schema from Alembic only; no runtime DDL."""
    return


def _row_to_version(row) -> Dict[str, Any]:
    created = row["created_at"]
    if hasattr(created, "isoformat"):
        created = created.isoformat()
    dag = row["dag_definition"]
    if isinstance(dag, str):
        try:
            dag = json.loads(dag)
        except (json.JSONDecodeError, TypeError):
            dag = {}
    return {
        "id": row["id"],
        "template_id": row["template_id"],
        "version": row["version"],
        "dag_definition": dag,
        "created_at": created,
    }


def create_version(
    template_id: int,
    version: str,
    dag_definition: Dict[str, Any],
) -> Dict[str, Any]:
    """Create a new version for a template. (template_id, version) must be unique."""
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    dag_json = json.dumps(dag_definition) if isinstance(dag_definition, dict) else "{}"
    created_at = datetime.utcnow()
    try:
        cur.execute(
            """
            INSERT INTO workflow_template_versions (template_id, version, dag_definition, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (template_id, version.strip(), dag_json, created_at),
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        if "UNIQUE" in str(e) or "unique" in str(e).lower():
            raise ValueError(f"Version '{version}' already exists for template {template_id}")
        raise
    return get_version(template_id, version)


def get_version(template_id: int, version: str) -> Optional[Dict[str, Any]]:
    """Return the version row for (template_id, version), or None."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT id, template_id, version, dag_definition, created_at
        FROM workflow_template_versions
        WHERE template_id = ? AND version = ?
        """,
        (template_id, version.strip()),
    )
    row = cur.fetchone()
    if row is None:
        return None
    return _row_to_version(row)


def get_latest_version(template_id: int) -> Optional[Dict[str, Any]]:
    """Return the version with the latest created_at for the template, or None."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT id, template_id, version, dag_definition, created_at
        FROM workflow_template_versions
        WHERE template_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (template_id,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    return _row_to_version(row)


def list_versions(template_id: int, limit: int = 100) -> List[Dict[str, Any]]:
    """List all versions for a template, newest first."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT id, template_id, version, dag_definition, created_at
        FROM workflow_template_versions
        WHERE template_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (template_id, limit),
    )
    return [_row_to_version(r) for r in cur.fetchall()]


def resolve_dag_for_run(template_id: int, version: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Resolve dag_definition for a run: if version is set, use that version's dag;
    otherwise use latest version's dag if any, else return None (caller uses template row).
    """
    if version is not None and version.strip():
        v = get_version(template_id, version)
        return v.get("dag_definition") if v else None
    v = get_latest_version(template_id)
    return v.get("dag_definition") if v else None
