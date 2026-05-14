"""
Auth sessions: track refresh tokens with ip_address and user_agent.

Table: auth_sessions (id, user_id, refresh_token_id, created_at, expires_at, ip_address, user_agent).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from database.db import db


def _ensure_schema() -> None:
    """Schema from Alembic only."""
    return


def create_session(
    user_id: int,
    refresh_token_id: int,
    expires_at: datetime,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> int:
    """Create session row linked to refresh token. Returns session id."""
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO auth_sessions (user_id, refresh_token_id, created_at, expires_at, ip_address, user_agent)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (user_id, refresh_token_id, datetime.utcnow(), expires_at, ip_address or None, user_agent or None),
    )
    conn.commit()
    return int(cur.lastrowid)


def list_sessions_for_user(user_id: int) -> List[Dict[str, Any]]:
    """Return list of active sessions for user (join with refresh_tokens to filter non-revoked)."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT s.id AS session_id, s.user_id, s.created_at, s.expires_at, s.ip_address, s.user_agent,
               r.revoked
        FROM auth_sessions s
        JOIN refresh_tokens r ON r.id = s.refresh_token_id
        WHERE s.user_id = ?
        ORDER BY s.created_at DESC
        """,
        (user_id,),
    )
    rows = cur.fetchall()
    out = []
    for row in rows:
        if row.get("revoked"):
            continue
        expires = row.get("expires_at")
        if expires and hasattr(expires, "timestamp") and expires.timestamp() < datetime.utcnow().timestamp():
            continue
        if expires and isinstance(expires, str) and expires < datetime.utcnow().isoformat():
            continue
        created = row.get("created_at")
        if hasattr(created, "isoformat"):
            created = created.isoformat()
        out.append({
            "session_id": row["session_id"],
            "user_id": row["user_id"],
            "created_at": created,
            "expires_at": row["expires_at"].isoformat() if hasattr(row.get("expires_at"), "isoformat") else row.get("expires_at"),
            "ip_address": row.get("ip_address") or None,
            "user_agent": row.get("user_agent") or None,
        })
    return out


def get_session_refresh_token_id(session_id: int) -> Optional[int]:
    """Return refresh_token_id for session if it exists."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute("SELECT refresh_token_id FROM auth_sessions WHERE id = ?", (session_id,))
    row = cur.fetchone()
    return int(row["refresh_token_id"]) if row else None


def get_session_user_id(session_id: int) -> Optional[int]:
    """Return user_id for session if it exists."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute("SELECT user_id FROM auth_sessions WHERE id = ?", (session_id,))
    row = cur.fetchone()
    return int(row["user_id"]) if row else None


def delete_session(session_id: int) -> bool:
    """Delete session row. Returns True if deleted. Caller should also revoke refresh token."""
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM auth_sessions WHERE id = ?", (session_id,))
    conn.commit()
    return cur.rowcount > 0
