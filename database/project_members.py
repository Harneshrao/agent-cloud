"""
Project-level membership and roles (UUID). Schema: Alembic only.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from database.models import Project, ProjectMember
from database.session import SessionLocal

PROJECT_ROLES = ("owner", "member", "viewer")
ROLES_CAN_MANAGE = ("owner",)
ROLES_CAN_RUN = ("owner", "member")
ROLES_CAN_VIEW = ("owner", "member", "viewer")


def get_project_role(project_id: uuid.UUID, user_id: uuid.UUID) -> Optional[str]:
    """Role from project_members, or owner if Project.user_id matches."""
    with SessionLocal() as session:
        row = session.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            )
        ).scalar_one_or_none()
        if row is not None:
            return row.role
        proj = session.get(Project, project_id)
        if proj is None:
            return None
        if proj.user_id == user_id:
            return "owner"
        return None


def add_project_member(
    project_id: uuid.UUID, user_id: uuid.UUID, role: str = "member"
) -> Dict[str, Any]:
    if role not in PROJECT_ROLES:
        raise ValueError(f"Role must be one of {PROJECT_ROLES}")
    now = datetime.utcnow()
    with SessionLocal() as session:
        try:
            m = ProjectMember(
                project_id=project_id, user_id=user_id, role=role, created_at=now
            )
            session.add(m)
            session.commit()
            session.refresh(m)
        except IntegrityError as e:
            session.rollback()
            raise ValueError("User is already a member of this project") from e
        return {
            "project_id": m.project_id,
            "user_id": m.user_id,
            "role": m.role,
            "created_at": m.created_at,
        }


def list_project_members(project_id: uuid.UUID) -> List[Dict[str, Any]]:
    with SessionLocal() as session:
        rows = session.execute(
            select(ProjectMember).where(ProjectMember.project_id == project_id)
        ).scalars().all()
        out = []
        for r in rows:
            ca = r.created_at
            out.append(
                {
                    "id": r.id,
                    "project_id": r.project_id,
                    "user_id": r.user_id,
                    "role": r.role,
                    "created_at": ca.isoformat() if hasattr(ca, "isoformat") else ca,
                }
            )
        return out


def set_project_member_role(
    project_id: uuid.UUID, user_id: uuid.UUID, role: str
) -> None:
    if role not in PROJECT_ROLES:
        raise ValueError(f"Role must be one of {PROJECT_ROLES}")
    with SessionLocal() as session:
        r = session.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            )
        ).scalar_one_or_none()
        if r is None:
            raise ValueError("Member not found")
        r.role = role
        session.commit()


def remove_project_member(project_id: uuid.UUID, user_id: uuid.UUID) -> None:
    with SessionLocal() as session:
        session.execute(
            delete(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            )
        )
        session.commit()
