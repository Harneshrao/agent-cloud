"""
Subscription plans and limits for usage quotas.

Table: plans
  id, name, monthly_run_limit, monthly_execution_time_limit_ms, price_usd, created_at
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from database.db import db


def _ensure_schema() -> None:
    """Schema from Alembic only; no runtime DDL."""
    return


def ensure_free_plan() -> Dict[str, Any]:
    """Create the default Free plan if it does not exist. Return the plan dict."""
    _ensure_schema()
    existing = get_plan_by_name("Free")
    if existing is not None:
        return existing
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO plans (name, monthly_run_limit, monthly_execution_time_limit_ms, price_usd, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("Free", 1000, 600_000, 0.0, datetime.utcnow()),
    )
    conn.commit()
    return get_plan_by_id(int(cur.lastrowid))


def get_plan_by_id(plan_id: int) -> Optional[Dict[str, Any]]:
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        "SELECT id, name, monthly_run_limit, monthly_execution_time_limit_ms, price_usd, created_at FROM plans WHERE id = ?",
        (plan_id,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    return _row_to_plan(row)


def get_plan_by_name(name: str) -> Optional[Dict[str, Any]]:
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        "SELECT id, name, monthly_run_limit, monthly_execution_time_limit_ms, price_usd, created_at FROM plans WHERE name = ?",
        (name,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    return _row_to_plan(row)


def list_plans() -> List[Dict[str, Any]]:
    """Return all plans, ensuring Free plan exists."""
    ensure_free_plan()
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT id, name, monthly_run_limit, monthly_execution_time_limit_ms, price_usd, created_at
        FROM plans
        ORDER BY price_usd ASC, name ASC
        """
    )
    return [_row_to_plan(r) for r in cur.fetchall()]


def _row_to_plan(row) -> Dict[str, Any]:
    created = row["created_at"]
    if hasattr(created, "isoformat"):
        created = created.isoformat()
    return {
        "id": row["id"],
        "name": row["name"],
        "monthly_run_limit": int(row["monthly_run_limit"]),
        "monthly_execution_time_limit_ms": int(row["monthly_execution_time_limit_ms"]),
        "price_usd": float(row["price_usd"]),
        "created_at": created,
    }
