"""
Workflow templates: reusable automation pipelines.

Table: workflow_templates
  id, name, description, author_user_id, dag_definition (JSON), created_at, run_count, last_run_at

Table: template_ratings (for ranking)
  id, template_id, project_id, rating, review, created_at
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from database.db import db


def _ensure_schema() -> None:
    """Schema from Alembic only; no runtime DDL."""
    return


def _row_to_template(row) -> Dict[str, Any]:
    created = row["created_at"]
    last_run = row.get("last_run_at")
    if hasattr(created, "isoformat"):
        created = created.isoformat()
    if last_run is not None and hasattr(last_run, "isoformat"):
        last_run = last_run.isoformat()
    dag = row["dag_definition"]
    if isinstance(dag, str):
        try:
            dag = json.loads(dag)
        except (json.JSONDecodeError, TypeError):
            dag = {}
    schema = row.get("input_schema")
    if isinstance(schema, str):
        try:
            schema = json.loads(schema) if schema.strip() else None
        except (json.JSONDecodeError, TypeError):
            schema = None
    if schema is not None and not isinstance(schema, dict):
        schema = None
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"] or "",
        "author_user_id": row["author_user_id"],
        "dag_definition": dag,
        "input_schema": schema,
        "visibility": (row.get("visibility") or "private").strip() or "private",
        "forked_from_template_id": row.get("forked_from_template_id"),
        "created_at": created,
        "run_count": int(row.get("run_count") or 0),
        "last_run_at": last_run,
    }


def create_template(
    name: str,
    description: str,
    author_user_id: int,
    dag_definition: Dict[str, Any],
    input_schema: Optional[Dict[str, Any]] = None,
    visibility: str = "private",
    forked_from_template_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Insert a workflow template. visibility: private, team, or public."""
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    dag_json = json.dumps(dag_definition) if isinstance(dag_definition, dict) else str(dag_definition)
    schema_json = json.dumps(input_schema) if input_schema and isinstance(input_schema, dict) else None
    vis = (visibility or "private").strip() or "private"
    created_at = datetime.utcnow()
    cur.execute(
        """
        INSERT INTO workflow_templates (name, description, author_user_id, dag_definition, created_at, run_count, input_schema, visibility, forked_from_template_id)
        VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?)
        """,
        (name, description or "", author_user_id, dag_json, created_at, schema_json, vis, forked_from_template_id),
    )
    conn.commit()
    return get_template_by_id(int(cur.lastrowid))


def get_template_by_id(template_id: int) -> Optional[Dict[str, Any]]:
    """Return template by id or None."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT id, name, description, author_user_id, dag_definition, created_at, run_count, last_run_at, input_schema, visibility, forked_from_template_id
        FROM workflow_templates
        WHERE id = ?
        """,
        (template_id,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    return _row_to_template(row)


def list_templates(limit: int = 100) -> List[Dict[str, Any]]:
    """Return all templates, newest first."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT id, name, description, author_user_id, dag_definition, created_at, run_count, last_run_at, input_schema, visibility, forked_from_template_id
        FROM workflow_templates
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (limit,),
    )
    return [_row_to_template(r) for r in cur.fetchall()]


def list_public_templates(limit: int = 100) -> List[Dict[str, Any]]:
    """Return templates with visibility = 'public', newest first."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT id, name, description, author_user_id, dag_definition, created_at, run_count, last_run_at, input_schema, visibility, forked_from_template_id
        FROM workflow_templates
        WHERE visibility = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        ("public", limit),
    )
    return [_row_to_template(r) for r in cur.fetchall()]


def fork_template(template_id: int, new_author_user_id: int) -> Dict[str, Any]:
    """
    Fork a template: copy metadata and latest version; fork is owned by new_author_user_id.
    Sets forked_from_template_id and visibility='private'. Returns the new template.
    """
    from database.template_versions import create_version, get_latest_version

    source = get_template_by_id(template_id)
    if source is None:
        raise ValueError(f"Template {template_id} not found")
    latest = get_latest_version(template_id)
    dag = (latest.get("dag_definition") if latest else None) or source.get("dag_definition") or {}
    name = f"Fork of {source.get('name', 'template')}"
    new_template = create_template(
        name=name,
        description=source.get("description") or "",
        author_user_id=new_author_user_id,
        dag_definition=dag,
        input_schema=source.get("input_schema"),
        visibility="private",
        forked_from_template_id=template_id,
    )
    if latest:
        try:
            create_version(
                template_id=new_template["id"],
                version=latest.get("version") or "1.0",
                dag_definition=latest.get("dag_definition") or dag,
            )
        except ValueError:
            pass
    return get_template_by_id(new_template["id"])


def record_template_run(template_id: int) -> None:
    """Increment run_count and set last_run_at. Call when a template is run."""
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    now = datetime.utcnow()
    cur.execute(
        """
        UPDATE workflow_templates
        SET run_count = run_count + 1, last_run_at = ?
        WHERE id = ?
        """,
        (now, template_id),
    )
    conn.commit()


def set_template_visibility(template_id: int, visibility: str) -> None:
    """Set template visibility to 'private', 'team', or 'public'."""
    _ensure_schema()
    vis = (visibility or "private").strip() or "private"
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE workflow_templates SET visibility = ? WHERE id = ?",
        (vis, template_id),
    )
    conn.commit()


# ---------- Template ratings (for ranking) ----------


def add_template_rating(
    template_id: int,
    project_id: int,
    rating: int,
    review: Optional[str] = None,
) -> Dict[str, Any]:
    """Add a rating for a template. Rating 1-5."""
    _ensure_schema()
    if not (1 <= rating <= 5):
        raise ValueError("rating must be between 1 and 5")
    conn = db.get_connection()
    cur = conn.cursor()
    created_at = datetime.utcnow()
    cur.execute(
        """
        INSERT INTO template_ratings (template_id, project_id, rating, review, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (template_id, project_id, rating, review or "", created_at),
    )
    conn.commit()
    return {
        "id": int(cur.lastrowid),
        "template_id": template_id,
        "project_id": project_id,
        "rating": rating,
        "review": review or "",
        "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at),
    }


def get_average_rating_for_template(template_id: int) -> Optional[float]:
    """Return average rating for a template, or None."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        "SELECT AVG(rating) AS avg_rating FROM template_ratings WHERE template_id = ?",
        (template_id,),
    )
    row = cur.fetchone()
    if row is None or row["avg_rating"] is None:
        return None
    return round(float(row["avg_rating"]), 2)


def get_ratings_for_template(template_id: int, limit: int = 100) -> List[Dict[str, Any]]:
    """Return ratings for a template."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT id, template_id, project_id, rating, review, created_at
        FROM template_ratings
        WHERE template_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (template_id, limit),
    )
    out = []
    for row in cur.fetchall():
        created = row["created_at"]
        if hasattr(created, "isoformat"):
            created = created.isoformat()
        out.append({
            "id": row["id"],
            "template_id": row["template_id"],
            "project_id": row["project_id"],
            "rating": row["rating"],
            "review": row["review"] or "",
            "created_at": created,
        })
    return out
