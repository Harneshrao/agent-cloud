"""
API keys for programmatic access.

Table: api_keys (id, user_id UUID, key_hash, name, created_at, last_used_at).
Keys are stored as hash only. Format: ak_live_<random>.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from database.db import db
from database.pg_compat import pg_errors


PREFIX = "ak_live_"


def _ensure_schema() -> None:
    """Schema from Alembic only."""
    return


def _hash_key(plain_key: str) -> str:
    return hashlib.sha256(plain_key.encode("utf-8")).hexdigest()


def _normalize_user_id(user_id: uuid.UUID | str) -> uuid.UUID:
    if isinstance(user_id, uuid.UUID):
        return user_id
    return uuid.UUID(str(user_id))


def create_key(user_id: uuid.UUID | str, name: str) -> Dict[str, Any]:
    """Create a new API key. Returns the key once (plain) and metadata."""
    _ensure_schema()
    uid = _normalize_user_id(user_id)
    plain = PREFIX + secrets.token_urlsafe(32)
    key_hash = _hash_key(plain)
    conn = db.get_connection()
    cur = conn.cursor()
    now = datetime.now(timezone.utc)
    try:
        cur.execute(
            """
            INSERT INTO api_keys (user_id, key_hash, name, created_at)
            VALUES (?, ?, ?, ?)
            RETURNING id
            """,
            (str(uid), key_hash, (name or "API Key").strip(), now),
        )
        row = cur.fetchone()
        conn.commit()
    except pg_errors.UndefinedTable:
        conn.rollback()
        raise RuntimeError(
            "api_keys table missing — run: alembic upgrade head"
        ) from None
    except Exception:
        conn.rollback()
        raise
    key_id = int(row["id"]) if row else int(cur.lastrowid or 0)
    return {
        "id": key_id,
        "key": plain,
        "name": (name or "API Key").strip(),
        "created_at": now.isoformat(),
    }


def get_user_by_key(plain_key: str) -> Optional[Dict[str, Any]]:
    """Return user dict if key is valid. Updates last_used_at."""
    _ensure_schema()
    if not plain_key.startswith(PREFIX) or len(plain_key) < len(PREFIX) + 16:
        return None
    key_hash = _hash_key(plain_key)
    conn = db.get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT id, user_id, name, created_at FROM api_keys WHERE key_hash = ?",
            (key_hash,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        now = datetime.now(timezone.utc)
        cur.execute("UPDATE api_keys SET last_used_at = ? WHERE id = ?", (now, row["id"]))
        conn.commit()
    except pg_errors.UndefinedTable:
        conn.rollback()
        return None
    except Exception:
        conn.rollback()
        raise
    from database.users import get_user_by_id

    uid = row["user_id"]
    if not isinstance(uid, uuid.UUID):
        uid = uuid.UUID(str(uid))
    return get_user_by_id(uid)


def list_keys_for_user(user_id: uuid.UUID | str) -> List[Dict[str, Any]]:
    """List API keys for a user (no plain key)."""
    _ensure_schema()
    uid = _normalize_user_id(user_id)
    cur = db.get_connection().cursor()
    try:
        cur.execute(
            """
            SELECT id, user_id, name, created_at, last_used_at
            FROM api_keys
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (str(uid),),
        )
        rows = cur.fetchall() or []
    except pg_errors.UndefinedTable:
        raise RuntimeError(
            "api_keys table missing — run: alembic upgrade head"
        ) from None
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "created_at": (
                r["created_at"].isoformat()
                if hasattr(r["created_at"], "isoformat")
                else r["created_at"]
            ),
            "last_used_at": (
                r["last_used_at"].isoformat()
                if r.get("last_used_at") and hasattr(r["last_used_at"], "isoformat")
                else r.get("last_used_at")
            ),
        }
        for r in rows
    ]


def delete_key(key_id: int, user_id: uuid.UUID | str) -> bool:
    """Delete an API key. Returns True if deleted (and key belonged to user)."""
    _ensure_schema()
    uid = _normalize_user_id(user_id)
    conn = db.get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "DELETE FROM api_keys WHERE id = ? AND user_id = ?",
            (key_id, str(uid)),
        )
        conn.commit()
        return cur.rowcount > 0
    except Exception:
        conn.rollback()
        raise
