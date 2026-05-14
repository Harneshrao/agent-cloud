"""
Workflow templates API: publish and run reusable automation pipelines.

Endpoints:
  POST /templates           - Create a template (auth required).
  GET  /templates           - List templates.
  GET  /templates/{id}      - Get one template.
  POST /templates/{id}/run  - Run template (project context, creates tasks from DAG).
  GET  /templates/top       - Top templates by runs, rating, recency.
  GET  /templates/trending  - Trending templates.
  POST /templates/{id}/rate - Rate a template (project context).
  GET  /templates/{id}/ratings - List ratings (optional).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from api.auth_api import get_current_user
from api.deps import require_project_context
from api.schemas.task_responses import TemplateRunResponse
from database.template_installs import get_install, install as install_template, delete_install
from database.template_publications import approve as approve_publication, get_publication, list_marketplace_templates, publish as publish_template
from database.workflow_templates import (
    add_template_rating,
    create_template,
    fork_template,
    get_average_rating_for_template,
    get_ratings_for_template,
    get_template_by_id,
    list_public_templates,
    list_templates,
)
from engine.quota_checker import check_quota
from engine.template_ranking import get_top_templates, get_trending_templates
from engine.template_runner import merge_template_inputs, run_template
from engine.dag_scheduler import start_distributed_workflow


router = APIRouter(prefix="/templates", tags=["templates"])


class CreateTemplateRequest(BaseModel):
    """Request body for POST /templates."""

    name: str = Field(..., description="Template name")
    description: str = Field("", description="Template description")
    dag_definition: dict = Field(..., description="DAG: { \"nodes\": [ {\"id\", \"agent\", \"task\", \"deps\"?} ] }")
    input_schema: dict | None = Field(None, description="Optional param schema, e.g. {\"topic\": \"string\", \"region\": \"string\"}")
    visibility: str = Field("private", description="Visibility: private, team, or public")


class RunTemplateRequest(BaseModel):
    """Request body for POST /templates/{id}/run."""

    task_override: str | None = Field(None, description="Optional task text override for the run")
    version: str | None = Field(None, description="Optional version; if omitted, latest version is used")
    inputs: dict | None = Field(None, description="Parameter values for {{key}} substitution, e.g. {\"topic\": \"AI startups\", \"region\": \"US\"}")
    distributed: bool = Field(False, description="If true, run as distributed DAG (one task per node across workers)")


class InstallTemplateRequest(BaseModel):
    """Request body for POST /templates/{id}/install."""

    config: dict | None = Field(None, description="Optional config for {{key}} substitution, e.g. {\"topic\": \"AI\", \"region\": \"US\"}")


class RateTemplateRequest(BaseModel):
    """Request body for POST /templates/{id}/rate."""

    rating: int = Field(..., ge=1, le=5)
    review: str | None = None


# ---------- Define /top and /trending before /{id} so they match first ----------


@router.get("/top")
def templates_top(limit: int = Query(20, ge=1, le=100)):
    """Return top templates ranked by runs, average rating, and recency."""
    try:
        templates = get_top_templates(limit=limit)
        return {"templates": templates}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trending")
def templates_trending(limit: int = Query(20, ge=1, le=100)):
    """Return trending templates (higher weight on recency)."""
    try:
        templates = get_trending_templates(limit=limit)
        return {"templates": templates}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/public")
def templates_public(limit: int = Query(100, ge=1, le=500)):
    """Return public templates (visibility = 'public')."""
    try:
        templates = list_public_templates(limit=limit)
        return {"templates": templates}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/marketplace")
def templates_marketplace(limit: int = Query(100, ge=1, le=500)):
    """Return marketplace templates: public and approved only."""
    try:
        templates = list_marketplace_templates(limit=limit)
        return {"templates": templates}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- CRUD ----------


@router.post("")
def post_templates(
    data: CreateTemplateRequest,
    user: dict = Depends(get_current_user),
):
    """Create a workflow template. Requires auth; author_user_id = current user."""
    try:
        template = create_template(
            name=data.name,
            description=data.description or "",
            author_user_id=user["id"],
            dag_definition=data.dag_definition,
            input_schema=data.input_schema,
            visibility=getattr(data, "visibility", None) or "private",
        )
        return {"status": "created", "template": template}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
def get_templates(limit: int = Query(100, ge=1, le=500)):
    """List all workflow templates."""
    try:
        templates = list_templates(limit=limit)
        return {"templates": templates}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{template_id}")
def get_template(template_id: int):
    """Get a single template by id."""
    template = get_template_by_id(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
    avg = get_average_rating_for_template(template_id)
    return {"template": {**template, "average_rating": avg}}


@router.post("/{template_id}/run", response_model=TemplateRunResponse)
def post_template_run(
    template_id: int,
    data: RunTemplateRequest | None = None,
    context: dict = Depends(require_project_context),
):
    """
    Run a template: parse dag_definition, create tasks for each node, link in task_graph.
    Requires project context and quota. Returns root_task_ids and all_task_ids.
    """
    if get_template_by_id(template_id) is None:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
    project_id = context["project_id"]
    check_quota(project_id)
    try:
        task_override = data.task_override if data else None
        version = data.version if data else None
        runtime_inputs = (data.inputs if data else None) or {}
        install = get_install(template_id, project_id)
        install_config = (install.get("config_json") if install else None) or {}
        merged_inputs = merge_template_inputs(install_config, runtime_inputs)
        if data and getattr(data, "distributed", False):
            workflow_id, root_ids = start_distributed_workflow(
                template_id,
                project_id,
                inputs=merged_inputs,
                task_override=task_override,
                version=version,
            )
            return TemplateRunResponse(
                status="started",
                distributed=True,
                template_id=template_id,
                project_id=project_id,
                workflow_id=workflow_id,
                root_task_ids=root_ids,
                task_ids=None,
            )
        root_ids, all_ids = run_template(
            template_id,
            project_id,
            task_override=task_override,
            version=version,
            inputs=merged_inputs,
        )
        return TemplateRunResponse(
            status="started",
            template_id=template_id,
            project_id=project_id,
            version=version,
            inputs=merged_inputs,
            root_task_ids=root_ids,
            task_ids=all_ids,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{template_id}/publish")
def post_template_publish(
    template_id: int,
    user: dict = Depends(get_current_user),
):
    """Submit template for publication (visibility=public, pending approval)."""
    if get_template_by_id(template_id) is None:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
    try:
        pub = publish_template(template_id)
        return {"status": "published", "publication": pub}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{template_id}/approve")
def post_template_approve(
    template_id: int,
    user: dict = Depends(get_current_user),
):
    """Approve a template for the marketplace."""
    if get_template_by_id(template_id) is None:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
    try:
        pub = approve_publication(template_id, user["id"])
        return {"status": "approved", "publication": pub}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{template_id}/fork")
def post_template_fork(
    template_id: int,
    user: dict = Depends(get_current_user),
):
    """Fork a template: copy metadata and latest version; fork is owned by the current user."""
    if get_template_by_id(template_id) is None:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
    try:
        new_template = fork_template(template_id, user["id"])
        return {"status": "created", "template": new_template}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{template_id}/install")
def post_template_install(
    template_id: int,
    data: InstallTemplateRequest | None = None,
    context: dict = Depends(require_project_context),
):
    """Install a template for the current project with optional config. Idempotent."""
    if get_template_by_id(template_id) is None:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
    project_id = context["project_id"]
    config = data.config if data and data.config else None
    install = install_template(template_id, project_id, config=config)
    return {"status": "installed", "install": install}


@router.delete("/{template_id}/install")
def delete_template_install(
    template_id: int,
    context: dict = Depends(require_project_context),
):
    """Uninstall the template for the current project."""
    project_id = context["project_id"]
    deleted = delete_install(template_id, project_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Template not installed for this project")
    return {"status": "uninstalled", "template_id": template_id, "project_id": project_id}


@router.post("/{template_id}/rate")
def post_template_rate(
    template_id: int,
    data: RateTemplateRequest,
    context: dict = Depends(require_project_context),
):
    """Rate a template from the current project."""
    if get_template_by_id(template_id) is None:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
    try:
        rating = add_template_rating(
            template_id=template_id,
            project_id=context["project_id"],
            rating=data.rating,
            review=data.review,
        )
        return {"status": "created", "rating": rating}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{template_id}/ratings")
def get_template_ratings(template_id: int, limit: int = Query(100, ge=1, le=500)):
    """List ratings for a template."""
    if get_template_by_id(template_id) is None:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
    ratings = get_ratings_for_template(template_id, limit=limit)
    avg = get_average_rating_for_template(template_id)
    return {"template_id": template_id, "ratings": ratings, "average_rating": avg}
