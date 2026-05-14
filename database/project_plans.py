"""
Project-to-plan assignment (UUID). Schema: Alembic only.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from database.db import db
from database.plans import ensure_free_plan, get_plan_by_id, get_plan_by_name


def _ensure_schema() -> None:
    """No runtime DDL — schema from Alembic."""
    return


def assign_plan(project_id: uuid.UUID, plan_id: int) -> Dict[str, Any]:
    """Record that a project is on a plan as of now."""
    _ensure_schema()
    plan = get_plan_by_id(plan_id)
    if plan is None:
        raise ValueError(f"Plan id {plan_id} not found")
    conn = db.get_connection()
    cur = conn.cursor()
    now = datetime.utcnow()
    cur.execute(
        """
        INSERT INTO project_plans (project_id, plan_id, started_at)
        VALUES (?, ?, ?)
        """,
        (project_id, plan_id, now),
    )
    conn.commit()
    return plan


def get_current_plan_for_project(project_id: uuid.UUID) -> Optional[Dict[str, Any]]:
    """Return the current plan for the project (latest started_at), or None."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT plan_id, started_at
        FROM project_plans
        WHERE project_id = ?
        ORDER BY started_at DESC
        LIMIT 1
        """,
        (project_id,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    return get_plan_by_id(int(row["plan_id"]))


def assign_free_plan_for_project(project_id: uuid.UUID) -> Dict[str, Any]:
    """Assign the Free plan to a project."""
    ensure_free_plan()
    free = get_plan_by_name("Free")
    if free is None:
        raise ValueError("Free plan not found")
    return assign_plan(project_id, free["id"])
