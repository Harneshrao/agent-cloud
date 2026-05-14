"""
Agent revenue: record revenue split (developer vs platform) per paid execution.

Table: agent_revenue (id, agent_name, developer_user_id, execution_cost, developer_share, platform_share, created_at)
Split: 70% developer, 30% platform. Developer share is added to developer_accounts.balance.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from database.db import db
from database.developer_accounts import add_balance

DEVELOPER_SHARE_RATIO = 0.7
PLATFORM_SHARE_RATIO = 0.3


def _ensure_schema() -> None:
    """Schema from Alembic only; no runtime DDL."""
    return


def record_revenue(
    agent_name: str,
    execution_cost: float,
    developer_user_id: Optional[int] = None,
) -> int:
    """
    Record a revenue event: compute developer_share (70%) and platform_share (30%),
    insert into agent_revenue, and add developer_share to developer_accounts.balance.
    Returns the new agent_revenue row id.
    """
    _ensure_schema()
    if execution_cost <= 0:
        return 0
    developer_share = round(execution_cost * DEVELOPER_SHARE_RATIO, 4)
    platform_share = round(execution_cost * PLATFORM_SHARE_RATIO, 4)
    now = datetime.utcnow()

    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO agent_revenue (agent_name, developer_user_id, execution_cost, developer_share, platform_share, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (agent_name, developer_user_id, execution_cost, developer_share, platform_share, now),
    )
    row_id = int(cur.lastrowid)
    if developer_user_id is not None and developer_share > 0:
        add_balance(developer_user_id, developer_share)
    conn.commit()
    return row_id


def get_revenue_summary(developer_user_id: int) -> Dict[str, Any]:
    """
    Return revenue summary for a developer: balance, total_earned, total_platform,
    recent rows from agent_revenue.
    """
    _ensure_schema()
    from database.developer_accounts import get_balance

    balance = get_balance(developer_user_id)
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COALESCE(SUM(developer_share), 0) AS total_earned,
               COALESCE(SUM(platform_share), 0) AS total_platform,
               COALESCE(SUM(execution_cost), 0) AS total_revenue
        FROM agent_revenue
        WHERE developer_user_id = ?
        """,
        (developer_user_id,),
    )
    row = cur.fetchone()
    total_earned = float(row["total_earned"]) if row else 0.0
    total_platform = float(row["total_platform"]) if row else 0.0
    total_revenue = float(row["total_revenue"]) if row else 0.0

    cur.execute(
        """
        SELECT id, agent_name, execution_cost, developer_share, platform_share, created_at
        FROM agent_revenue
        WHERE developer_user_id = ?
        ORDER BY created_at DESC
        LIMIT 50
        """,
        (developer_user_id,),
    )
    recent = []
    for r in cur.fetchall():
        recent.append({
            "id": r["id"],
            "agent_name": r["agent_name"],
            "execution_cost": float(r["execution_cost"]),
            "developer_share": float(r["developer_share"]),
            "platform_share": float(r["platform_share"]),
            "created_at": r["created_at"].isoformat() if hasattr(r["created_at"], "isoformat") else str(r["created_at"]),
        })

    return {
        "balance": balance,
        "total_earned": total_earned,
        "total_platform": total_platform,
        "total_revenue": total_revenue,
        "recent": recent,
    }
