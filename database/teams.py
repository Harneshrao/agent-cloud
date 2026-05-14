"""
Multi-tenant: teams and team membership.

Tables: teams (id, name, created_at),
       team_members (team_id, user_id, role, created_at) with UNIQUE(team_id, user_id).
Roles: owner, admin, member. Only owners and admins can modify project/team settings.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from database.db import db

ROLES = ("owner", "admin", "member")
ROLES_CAN_MANAGE = ("owner", "admin")


def _ensure_schema() -> None:
    """Schema from Alembic only; no runtime DDL."""
    return


def create_team(name: str, owner_user_id: int) -> Dict[str, Any]:
    """Create a team and add the user as owner. Returns the team dict."""
    _ensure_schema()
    name = (name or "").strip()
    if not name:
        raise ValueError("Team name required")
    conn = db.get_connection()
    cur = conn.cursor()
    now = datetime.utcnow()
    cur.execute(
        "INSERT INTO teams (name, created_at) VALUES (?, ?)",
        (name, now),
    )
    conn.commit()
    team_id = int(cur.lastrowid)
    cur.execute(
        """
        INSERT INTO team_members (team_id, user_id, role, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (team_id, owner_user_id, "owner", now),
    )
    conn.commit()
    return get_team_by_id(team_id)


def get_team_by_id(team_id: int) -> Optional[Dict[str, Any]]:
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        "SELECT id, name, created_at FROM teams WHERE id = ?",
        (team_id,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    return _row_to_team_dict(row)


def list_teams_for_user(user_id: int) -> List[Dict[str, Any]]:
    """Return all teams the user is a member of, with their role."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT t.id, t.name, t.created_at, tm.role
        FROM teams t
        INNER JOIN team_members tm ON tm.team_id = t.id
        WHERE tm.user_id = ?
        ORDER BY t.name
        """,
        (user_id,),
    )
    rows = cur.fetchall()
    return [_row_to_team_dict(r, role=r["role"]) for r in rows]


def _row_to_team_dict(row, role: Optional[str] = None) -> Dict[str, Any]:
    created = row["created_at"]
    if hasattr(created, "isoformat"):
        created = created.isoformat()
    out = {
        "id": row["id"],
        "name": row["name"],
        "created_at": created,
    }
    if role is not None:
        out["role"] = role
    return out


def get_member_role(team_id: int, user_id: int) -> Optional[str]:
    """Return the user's role in the team, or None if not a member."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        "SELECT role FROM team_members WHERE team_id = ? AND user_id = ?",
        (team_id, user_id),
    )
    row = cur.fetchone()
    return row["role"] if row else None


def user_can_manage_team(team_id: int, user_id: int) -> bool:
    """True if user is owner or admin of the team."""
    role = get_member_role(team_id, user_id)
    return role in ROLES_CAN_MANAGE if role else False


def add_team_member(team_id: int, user_id: int, role: str = "member") -> None:
    """Add a user to a team. Caller must be owner/admin. Raises if already member."""
    _ensure_schema()
    if role not in ROLES:
        raise ValueError(f"Role must be one of {ROLES}")
    conn = db.get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO team_members (team_id, user_id, role, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (team_id, user_id, role, datetime.utcnow()),
        )
        conn.commit()
    except Exception as e:
        if "UNIQUE" in str(e) or "primary" in str(e).lower():
            raise ValueError("User is already a member of this team") from e
        raise

