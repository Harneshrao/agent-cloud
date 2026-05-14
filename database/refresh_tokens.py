"""
Refresh tokens for secure session management.

Table: refresh_tokens (id, user_id, token_hash, expires_at, created_at, revoked).
- Only hash is stored; 30-day expiration.
- Max 5 active tokens per user; oldest revoked when exceeding.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from database.db import db

REFRESH_EXPIRATION_DAYS = 30
MAX_ACTIVE_TOKENS_PER_USER = 5


def _ensure_schema() -> None:
    """Schema from Alembic only."""
    return


def _hash_token(plain: str) -> str:
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()


def create_refresh_token(user_id: int) -> tuple[str, int]:
    """
    Generate a new refresh token, store its hash, enforce max 5 per user.
    Returns (plain_token, token_row_id). Caller must return plain_token to client once.
    """
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    # Enforce max active per user: delete oldest (by created_at) if at limit
    cur.execute(
        """
        SELECT id FROM refresh_tokens
        WHERE user_id = ? AND (revoked = 0 AND (expires_at IS NULL OR expires_at > NOW() AT TIME ZONE 'UTC'))
        ORDER BY created_at ASC
        """,
        (user_id,),
    )
    active = cur.fetchall()
    to_remove = len(active) - (MAX_ACTIVE_TOKENS_PER_USER - 1)  # keep 4, add 1 = 5
    if to_remove > 0:
        for row in active[:to_remove]:
            cur.execute("UPDATE refresh_tokens SET revoked = 1 WHERE id = ?", (row["id"],))
    plain = secrets.token_urlsafe(48)
    token_hash = _hash_token(plain)
    expires_at = datetime.utcnow() + timedelta(days=REFRESH_EXPIRATION_DAYS)
    created_at = datetime.utcnow()
    cur.execute(
        """
        INSERT INTO refresh_tokens (user_id, token_hash, expires_at, created_at, revoked)
        VALUES (?, ?, ?, ?, 0)
        """,
        (user_id, token_hash, expires_at, created_at),
    )
    conn.commit()
    return plain, int(cur.lastrowid)


def get_by_token(plain_token: str) -> Optional[Dict[str, Any]]:
    """Return refresh token row (id, user_id, expires_at, created_at, revoked) if valid and not revoked/expired."""
    _ensure_schema()
    token_hash = _hash_token(plain_token)
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT id, user_id, expires_at, created_at, revoked
        FROM refresh_tokens
        WHERE token_hash = ?
        """,
        (token_hash,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    if row["revoked"]:
        return None
    expires_at = row["expires_at"]
    if hasattr(expires_at, "timestamp"):
        if expires_at.timestamp() < datetime.utcnow().timestamp():
            return None
    elif expires_at and str(expires_at) < datetime.utcnow().isoformat():
        return None
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "expires_at": row["expires_at"],
        "created_at": row["created_at"],
        "revoked": row["revoked"],
    }


def get_revoked_token_user_id(plain_token: str) -> Optional[int]:
    """If token exists but is revoked (reuse detection), return user_id; else None."""
    _ensure_schema()
    token_hash = _hash_token(plain_token)
    cur = db.get_connection().cursor()
    cur.execute(
        "SELECT user_id, revoked FROM refresh_tokens WHERE token_hash = ?",
        (token_hash,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    if row.get("revoked"):
        return int(row["user_id"])
    return None


def revoke_all_for_user(user_id: int) -> int:
    """Revoke all refresh tokens for user. Returns count revoked."""
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE refresh_tokens SET revoked = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    return cur.rowcount


def revoke_by_id(token_id: int) -> bool:
    """Revoke a refresh token by id. Returns True if a row was updated."""
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE refresh_tokens SET revoked = 1 WHERE id = ?", (token_id,))
    conn.commit()
    return cur.rowcount > 0


def revoke_by_token(plain_token: str) -> bool:
    """Revoke a refresh token by plain token (hash lookup). Returns True if found and revoked."""
    _ensure_schema()
    token_hash = _hash_token(plain_token)
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE refresh_tokens SET revoked = 1 WHERE token_hash = ?", (token_hash,))
    conn.commit()
    return cur.rowcount > 0


def count_active_per_user(user_id: int) -> int:
    """Count non-revoked, non-expired refresh tokens for user."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT COUNT(*) AS n FROM refresh_tokens
        WHERE user_id = ? AND revoked = 0 AND expires_at > NOW() AT TIME ZONE 'UTC'
        """,
        (user_id,),
    )
    row = cur.fetchone()
    return row["n"] if row else 0
