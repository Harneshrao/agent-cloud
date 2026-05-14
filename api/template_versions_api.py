"""
Versioned workflow templates API.

Endpoints:
  POST /templates/{id}/versions        - Create a new version.
  GET  /templates/{id}/versions       - List versions for a template.
  GET  /templates/{id}/versions/{ver} - Get one version by version string.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from api.auth_api import get_current_user
from database.workflow_templates import get_template_by_id
from database.template_versions import (
    create_version,
    get_version,
    list_versions,
)


router = APIRouter(prefix="/templates", tags=["templates"])


class CreateVersionRequest(BaseModel):
    """Request body for POST /templates/{id}/versions."""

    version: str = Field(..., description="Version string (e.g. 1.0, v2)")
    dag_definition: dict = Field(
        ...,
        description="DAG: { \"nodes\": [ {\"id\", \"agent\", \"task\", \"deps\"?} ] }",
    )


@router.post("/{template_id}/versions")
def post_template_versions(
    template_id: int,
    data: CreateVersionRequest,
    user: dict = Depends(get_current_user),
):
    """Create a new version for a template. (template_id, version) must be unique."""
    if get_template_by_id(template_id) is None:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
    try:
        version = create_version(
            template_id=template_id,
            version=data.version,
            dag_definition=data.dag_definition,
        )
        return {"status": "created", "version": version}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{template_id}/versions")
def get_template_versions(
    template_id: int,
    limit: int = Query(100, ge=1, le=500),
):
    """List all versions for a template, newest first."""
    if get_template_by_id(template_id) is None:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
    versions = list_versions(template_id, limit=limit)
    return {"template_id": template_id, "versions": versions}


@router.get("/{template_id}/versions/{version}")
def get_template_version(template_id: int, version: str):
    """Get a specific version by version string."""
    if get_template_by_id(template_id) is None:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
    v = get_version(template_id, version)
    if v is None:
        raise HTTPException(
            status_code=404,
            detail=f"Version '{version}' not found for template {template_id}",
        )
    return {"version": v}
