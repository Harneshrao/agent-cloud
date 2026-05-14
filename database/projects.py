"""
Projects — PostgreSQL UUID only (Alembic + SQLAlchemy).

Ownership: Project.user_id. Additional access via project_members.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from config.settings import DEFAULT_USER_UUID
from database.models import Project, ProjectMember
from database.project_plans import assign_free_plan_for_project
from database.project_members import ROLES_CAN_MANAGE as PROJECT_ROLES_CAN_MANAGE
from database.session import SessionLocal


def _project_to_dict(p: Project) -> Dict[str, Any]:
    created = p.created_at
    if hasattr(created, "isoformat"):
        created = created.isoformat()
    return {
        "id": p.id,
        "user_id": p.user_id,
        "name": p.name,
        "created_at": created,
    }


def create_project(user_id: uuid.UUID, name: str) -> Dict[str, Any]:
    """Create a project owned by user_id."""
    name = (name or "").strip()
    if not name:
        raise ValueError("Project name required")
    with SessionLocal() as session:
        p = Project(user_id=user_id, name=name)
        session.add(p)
        session.commit()
        session.refresh(p)
        pid = p.id
    try:
        assign_free_plan_for_project(pid)
    except Exception:
        pass
    try:
        from database.project_members import add_project_member

        add_project_member(pid, user_id, "owner")
    except Exception:
        pass
    with SessionLocal() as session:
        p2 = session.get(Project, pid)
        return _project_to_dict(p2) if p2 else {}


def get_project_by_id(project_id: uuid.UUID) -> Optional[Dict[str, Any]]:
    with SessionLocal() as session:
        p = session.get(Project, project_id)
        return _project_to_dict(p) if p else None


def list_projects_for_user(user_id: uuid.UUID) -> List[Dict[str, Any]]:
    """All projects owned by or joined via project_members."""
    with SessionLocal() as session:
        owned = session.execute(
            select(Project).where(Project.user_id == user_id)
        ).scalars().all()
        member_pids = session.execute(
            select(ProjectMember.project_id).where(ProjectMember.user_id == user_id)
        ).scalars().all()
        extra: List[Project] = []
        for pid in member_pids:
            if pid not in {o.id for o in owned}:
                op = session.get(Project, pid)
                if op:
                    extra.append(op)
        seen = set()
        out: List[Dict[str, Any]] = []
        for p in list(owned) + extra:
            if p.id in seen:
                continue
            seen.add(p.id)
            out.append(_project_to_dict(p))
        out.sort(key=lambda x: str(x.get("name", "")))
        return out


def user_can_access_project(project_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    if (
        str(user_id) == DEFAULT_USER_UUID
        and os.environ.get("ALLOW_ANONYMOUS_DEV", "").strip().lower() in ("1", "true", "yes")
    ):
        return True
    with SessionLocal() as session:
        proj = session.get(Project, project_id)
        if proj is None:
            return False
        if proj.user_id == user_id:
            return True
        m = session.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            )
        ).scalar_one_or_none()
        return m is not None


def user_can_manage_project(project_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    from database.project_members import get_project_role

    role = get_project_role(project_id, user_id)
    if role and role in PROJECT_ROLES_CAN_MANAGE:
        return True
    return False
