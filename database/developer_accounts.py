"""
Developer accounts: balance for agent revenue payouts.

Table: developer_accounts (user_id UNIQUE, balance REAL, created_at)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from database.db import db


def _ensure_schema() -> None:
    """Schema from Alembic only; no runtime DDL."""
    return


def get_or_create(user_id: int) -> Dict[str, Any]:
    """Get developer account; create with balance 0 if missing."""
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT user_id, balance, created_at FROM developer_accounts WHERE user_id = ?",
        (user_id,),
    )
    row = cur.fetchone()
    if row is not None:
        return {
            "user_id": row["user_id"],
            "balance": float(row["balance"]) if row["balance"] is not None else 0.0,
            "created_at": row["created_at"],
        }
    now = datetime.utcnow()
    cur.execute(
        "INSERT INTO developer_accounts (user_id, balance, created_at) VALUES (?, 0, ?)",
        (user_id, now),
    )
    conn.commit()
    return {"user_id": user_id, "balance": 0.0, "created_at": now}


def add_balance(user_id: int, amount: float) -> float:
    """Add amount to developer balance. Creates account if needed. Returns new balance."""
    _ensure_schema()
    get_or_create(user_id)
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE developer_accounts SET balance = balance + ? WHERE user_id = ?",
        (amount, user_id),
    )
    conn.commit()
    cur.execute("SELECT balance FROM developer_accounts WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    return float(row["balance"]) if row and row["balance"] is not None else 0.0


def get_balance(user_id: int) -> float:
    """Return current balance; 0 if no account."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute("SELECT balance FROM developer_accounts WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    return float(row["balance"]) if row and row["balance"] is not None else 0.0
