"""
Template publications and approval for marketplace.

Table: template_publications
  template_id (unique), approved (BOOLEAN), approved_by_user_id, approved_at
Only approved templates appear in GET /templates/marketplace.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from database.db import db
from database.workflow_templates import get_template_by_id, set_template_visibility


def _ensure_schema() -> None:
    """Schema from Alembic only; no runtime DDL."""
    return


def _row_to_publication(row) -> Dict[str, Any]:
    at = row.get("approved_at")
    if at is not None and hasattr(at, "isoformat"):
        at = at.isoformat()
    return {
        "template_id": row["template_id"],
        "approved": bool(row.get("approved")),
        "approved_by_user_id": row.get("approved_by_user_id"),
        "approved_at": at,
    }


def publish(template_id: int) -> Dict[str, Any]:
    """
    Submit template for publication: set visibility to 'public' and create/update
    publication row with approved=false. Returns the publication row.
    """
    _ensure_schema()
    if get_template_by_id(template_id) is None:
        raise ValueError(f"Template {template_id} not found")
    set_template_visibility(template_id, "public")
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO template_publications (template_id, approved, approved_by_user_id, approved_at)
        VALUES (?, 0, NULL, NULL)
        ON CONFLICT(template_id) DO UPDATE SET
            approved = 0,
            approved_by_user_id = NULL,
            approved_at = NULL
        """,
        (template_id,),
    )
    conn.commit()
    return get_publication(template_id)


def approve(template_id: int, approved_by_user_id: int) -> Dict[str, Any]:
    """Set template as approved. Creates publication row if missing."""
    _ensure_schema()
    if get_template_by_id(template_id) is None:
        raise ValueError(f"Template {template_id} not found")
    conn = db.get_connection()
    cur = conn.cursor()
    now = datetime.utcnow()
    cur.execute(
        """
        INSERT INTO template_publications (template_id, approved, approved_by_user_id, approved_at)
        VALUES (?, 1, ?, ?)
        ON CONFLICT(template_id) DO UPDATE SET
            approved = 1,
            approved_by_user_id = excluded.approved_by_user_id,
            approved_at = excluded.approved_at
        """,
        (template_id, approved_by_user_id, now),
    )
    conn.commit()
    return get_publication(template_id)


def get_publication(template_id: int) -> Optional[Dict[str, Any]]:
    """Return the publication row for template_id, or None."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT template_id, approved, approved_by_user_id, approved_at
        FROM template_publications
        WHERE template_id = ?
        """,
        (template_id,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    return _row_to_publication(row)


def list_marketplace_templates(limit: int = 100) -> List[Dict[str, Any]]:
    """
    Return templates that are both visibility='public' and approved.
    Only these appear in the public marketplace.
    """
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT t.id, t.name, t.description, t.author_user_id, t.dag_definition, t.created_at,
               t.run_count, t.last_run_at, t.input_schema, t.visibility, t.forked_from_template_id
        FROM workflow_templates t
        INNER JOIN template_publications p ON p.template_id = t.id
        WHERE t.visibility = 'public' AND p.approved = 1
        ORDER BY t.created_at DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cur.fetchall()
    from database.workflow_templates import _row_to_template  # avoid circular import
    return [_row_to_template(r) for r in rows]
