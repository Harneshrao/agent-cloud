"""
API keys for programmatic access.

Table: api_keys (id, user_id, key_hash, name, created_at, last_used_at).
Keys are stored as hash only. Format: ak_live_<random>.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime
from typing import Any, Dict, List, Optional

from database.db import db


PREFIX = "ak_live_"


def _ensure_schema() -> None:
    """Schema from Alembic only."""
    return


def _hash_key(plain_key: str) -> str:
    return hashlib.sha256(plain_key.encode("utf-8")).hexdigest()


def create_key(user_id: int, name: str) -> Dict[str, Any]:
    """Create a new API key. Returns the key once (plain) and metadata. Store plain key securely."""
    _ensure_schema()
    plain = PREFIX + secrets.token_urlsafe(32)
    key_hash = _hash_key(plain)
    conn = db.get_connection()
    cur = conn.cursor()
    now = datetime.utcnow()
    cur.execute(
        """
        INSERT INTO api_keys (user_id, key_hash, name, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, key_hash, (name or "API Key").strip(), now),
    )
    conn.commit()
    key_id = int(cur.lastrowid)
    return {
        "id": key_id,
        "key": plain,
        "name": (name or "API Key").strip(),
        "created_at": now.isoformat() if hasattr(now, "isoformat") else str(now),
    }


def get_user_by_key(plain_key: str) -> Optional[Dict[str, Any]]:
    """Return user dict if key is valid. Updates last_used_at."""
    _ensure_schema()
    if not plain_key.startswith(PREFIX) or len(plain_key) < len(PREFIX) + 16:
        return None
    key_hash = _hash_key(plain_key)
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, user_id, name, created_at FROM api_keys WHERE key_hash = ?",
        (key_hash,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    now = datetime.utcnow()
    cur.execute("UPDATE api_keys SET last_used_at = ? WHERE id = ?", (now, row["id"]))
    conn.commit()
    from database.users import get_user_by_id_full
    return get_user_by_id_full(int(row["user_id"]))


def list_keys_for_user(user_id: int) -> List[Dict[str, Any]]:
    """List API keys for a user (no plain key)."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT id, user_id, name, created_at, last_used_at
        FROM api_keys
        WHERE user_id = ?
        ORDER BY created_at DESC
        """,
        (user_id,),
    )
    rows = cur.fetchall() or []
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "created_at": r["created_at"].isoformat() if hasattr(r["created_at"], "isoformat") else r["created_at"],
            "last_used_at": r["last_used_at"].isoformat() if r.get("last_used_at") and hasattr(r["last_used_at"], "isoformat") else r.get("last_used_at"),
        }
        for r in rows
    ]


def delete_key(key_id: int, user_id: int) -> bool:
    """Delete an API key. Returns True if deleted (and key belonged to user)."""
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM api_keys WHERE id = ? AND user_id = ?", (key_id, user_id))
    conn.commit()
    return cur.rowcount > 0
