"""
Shared dependencies for project-scoped and admin APIs.

- require_project_id: X-Project-ID or project_id query (UUID).
- require_project_context: auth + project membership; returns user, project_id (UUID), role.
- require_admin: user.is_admin must be True (from DB).
"""

from __future__ import annotations

import uuid
from typing import Any, Dict

from fastapi import Depends, Header, HTTPException, Query, Request

from api.auth_api import get_current_user
from api.security_logger import log_unauthorized_access, log_unauthorized_project_access
from database.project_members import get_project_role, ROLES_CAN_RUN
from database.projects import user_can_access_project


def _parse_project_uuid(raw: str | None) -> uuid.UUID:
    if raw is None or not str(raw).strip():
        raise HTTPException(
            status_code=400,
            detail="Project context required: set X-Project-ID header or project_id query (UUID)",
        )
    try:
        return uuid.UUID(str(raw).strip())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="X-Project-ID must be a valid UUID",
        ) from None


def require_project_id(
    x_project_id: str | None = Header(None, alias="X-Project-ID"),
    project_id: str | None = Query(None, description="Project UUID"),
) -> uuid.UUID:
    """Extract project UUID from X-Project-ID header or project_id query."""
    pid = x_project_id if x_project_id is not None else project_id
    return _parse_project_uuid(pid)


def require_project_context(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user),
    project_id: uuid.UUID = Depends(require_project_id),
) -> Dict[str, Any]:
    """
    Dependency: require auth + project_id, verify user belongs to project.
    Returns {"user": user_dict, "project_id": uuid.UUID, "role": str}.
    """
    uid = user["id"]
    if not isinstance(uid, uuid.UUID):
        raise HTTPException(status_code=500, detail="Invalid user identity")
    if not user_can_access_project(project_id, uid):
        log_unauthorized_project_access(
            str(uid),
            str(project_id),
            client_host=request.client.host if request.client else None,
            path=getattr(request.url, "path", "") if request.url else "",
        )
        log_unauthorized_access("Access denied to this project", status_code=403)
        raise HTTPException(status_code=403, detail="Access denied to this project")
    role = get_project_role(project_id, uid) or "member"
    return {"user": user, "project_id": project_id, "role": role}


def require_project_can_run(
    context: Dict[str, Any] = Depends(require_project_context),
) -> Dict[str, Any]:
    """Dependency: require project context and role in (owner, member). Viewers get 403."""
    if context.get("role") not in ROLES_CAN_RUN:
        log_unauthorized_access(
            "Project role cannot run agents (viewer is read-only)", status_code=403
        )
        raise HTTPException(
            status_code=403, detail="Viewer role cannot run agents"
        )
    return context


def require_admin(
    user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Dependency: only users with is_admin=True (from DB) can access.
    Used for /system/*, /workers/*, /metrics/*, /alerts/*.
    """
    if not user.get("is_admin"):
        log_unauthorized_access("Admin access required", status_code=403)
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
