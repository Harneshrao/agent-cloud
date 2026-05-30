"""
Projects API: list and create projects. Multi-tenant UUID scope.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from database.projects import (
    create_project as db_create_project,
    list_projects_for_user,
    user_can_access_project,
    user_can_manage_project,
)
from database.template_installs import list_installs_for_project
from database.workflow_templates import get_template_by_id
from api.auth_api import get_current_user

router = APIRouter(prefix="/projects", tags=["projects"])


class CreateProjectRequest(BaseModel):
    name: str = Field(..., min_length=1, description="Project name")


@router.get("")
def list_projects(user: dict = Depends(get_current_user)):
    """List projects the current user can access."""
    uid = user["id"]
    if not isinstance(uid, uuid.UUID):
        raise HTTPException(status_code=500, detail="Invalid user identity")
    projects = list_projects_for_user(uid)
    return {"projects": projects}


@router.post("")
def create_project(
    data: CreateProjectRequest,
    user: dict = Depends(get_current_user),
):
    """Create a project owned by the current user."""
    uid = user["id"]
    if not isinstance(uid, uuid.UUID):
        raise HTTPException(status_code=500, detail="Invalid user identity")
    try:
        project = db_create_project(user_id=uid, name=data.name.strip())
        try:
            from services.product_analytics import track_project_created

            track_project_created(
                uid,
                uuid.UUID(project["id"]),
                name=data.name.strip(),
            )
        except Exception:
            pass
        return {"project": project}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{project_id}/templates")
def list_project_templates(
    project_id: uuid.UUID,
    user: dict = Depends(get_current_user),
):
    """List templates installed for the project."""
    uid = user["id"]
    if not isinstance(uid, uuid.UUID):
        raise HTTPException(status_code=500, detail="Invalid user identity")
    if not user_can_access_project(project_id, uid):
        raise HTTPException(status_code=403, detail="Access denied to this project")
    installs = list_installs_for_project(project_id)
    out = []
    for inst in installs:
        template = get_template_by_id(inst["template_id"])
        out.append({
            "install": inst,
            "template": template,
        })
    return {"project_id": str(project_id), "templates": out}
