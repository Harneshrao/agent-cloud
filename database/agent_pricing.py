"""
Agent pricing: per-execution price for monetization.

Table: agent_pricing (agent_name, price_per_run, currency, created_at)
Populated when agents are registered with price_per_run; used for billing and store display.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from database.db import db
from database.pg_compat import pg_errors


def _ensure_schema() -> None:
    """Schema from Alembic only; no runtime DDL."""
    return


def upsert_agent_pricing(
    agent_name: str,
    price_per_run: float,
    currency: str = "USD",
    developer_user_id: Optional[int] = None,
) -> None:
    """Insert or replace pricing for an agent (e.g. when agent is registered)."""
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    now = datetime.utcnow()
    cur.execute(
        """
        INSERT INTO agent_pricing (agent_name, price_per_run, currency, developer_user_id, created_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(agent_name) DO UPDATE SET
            price_per_run = excluded.price_per_run,
            currency = excluded.currency,
            developer_user_id = CASE WHEN excluded.developer_user_id IS NOT NULL THEN excluded.developer_user_id ELSE agent_pricing.developer_user_id END
        """,
        (agent_name, price_per_run, currency, developer_user_id, now),
    )
    conn.commit()


def set_agent_developer(agent_name: str, developer_user_id: int) -> None:
    """Set the developer (user_id) for an agent; used for revenue sharing when publishing."""
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE agent_pricing SET developer_user_id = ? WHERE agent_name = ?",
        (developer_user_id, agent_name),
    )
    conn.commit()


def get_price(agent_name: str) -> Optional[Dict[str, Any]]:
    """Return pricing for an agent, or None if not set. Includes developer_user_id for revenue."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        "SELECT agent_name, price_per_run, currency, developer_user_id, created_at FROM agent_pricing WHERE agent_name = ?",
        (agent_name,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    return {
        "agent_name": row["agent_name"],
        "price_per_run": float(row["price_per_run"]),
        "currency": row["currency"],
        "developer_user_id": row["developer_user_id"] if row.get("developer_user_id") is not None else None,
        "created_at": row["created_at"],
    }
