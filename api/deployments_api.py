"""
Wedge deployment API — upload artifacts, deploy, run, rollback.

Project-scoped via X-Project-ID. No marketplace coupling.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from agent_cloud.core.deployments.service import DeploymentApplicationService
from api.api_errors import deployment_already_active, deployment_error, quota_error, upload_error
from api.deps import require_project_can_run, require_project_context
from api.schemas.task_responses import AgentsV2RunResponse
from engine.quota_checker import QuotaExceeded
from services.task_service import enqueue_task

router = APIRouter(prefix="/deployments", tags=["deployments"])
_svc = DeploymentApplicationService()
_ONBOARDING_SAMPLES = frozenset({"sample_echo", "sample_fail", "sample_slow"})


class DeployFromArtifactRequest(BaseModel):
    artifact_id: str = Field(..., description="Validated artifact UUID")
    configuration: Dict[str, Any] = Field(default_factory=dict)


class RunDeploymentRequest(BaseModel):
    input: Dict[str, Any] = Field(default_factory=dict)
    task_text: str = Field("Run deployed agent", description="Task description")


@router.post("/onboarding/sample/{sample_name}")
async def deploy_onboarding_sample(
    sample_name: str,
    context: dict = Depends(require_project_can_run),
):
    """
    One-click first success: package a built-in sample agent, upload, and deploy.
    Allowed: sample_echo, sample_fail, sample_slow.
    """
    if sample_name not in _ONBOARDING_SAMPLES:
        raise HTTPException(
            status_code=404,
            detail=deployment_error(f"Unknown sample '{sample_name}'"),
        )
    project_id = context["project_id"]
    user_id = context.get("user", {}).get("id")
    try:
        from agent_cloud.core.deployments.samples import read_sample_manifest

        manifest = read_sample_manifest(sample_name)
        from database import deployment_store as _dep_store

        active = _dep_store.find_active_deployment(project_id, manifest["name"])
        if active and active.get("version") == manifest["version"]:
            raise HTTPException(
                status_code=409,
                detail=deployment_already_active(active),
            )
    except HTTPException:
        raise
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=404, detail=deployment_error(str(e))) from e
    try:
        from database import product_events as pe
        from services.product_analytics import track

        track(
            pe.EVENT_DEPLOYMENT_SAMPLE,
            user_id=user_id,
            project_id=project_id,
            properties={"sample": sample_name},
        )
    except Exception:
        pass
    try:
        from agent_cloud.core.deployments.samples import build_sample_zip

        data = build_sample_zip(sample_name)
        from services.quota_service import check_artifact_upload

        check_artifact_upload(project_id, len(data))
    except QuotaExceeded as e:
        raise HTTPException(status_code=429, detail=quota_error(str(e))) from e
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=deployment_error(str(e))) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=upload_error(str(e))) from e
    try:
        from services.quota_service import check_deployment_quota

        check_deployment_quota(project_id)
        artifact = _svc.upload_artifact(project_id, data, version=None)
        dep = _svc.deploy(project_id, uuid.UUID(artifact["artifact_id"]))
        try:
            from services.product_analytics import track_deployment_created

            track_deployment_created(
                project_id,
                uuid.UUID(dep["deployment_id"]),
                user_id=user_id,
                sample=sample_name,
            )
        except Exception:
            pass
        return {
            "message": f"Sample '{sample_name}' deployed",
            "artifact": artifact,
            "deployment": dep,
        }
    except QuotaExceeded as e:
        raise HTTPException(status_code=429, detail=quota_error(str(e))) from e
    except ValueError as e:
        try:
            from database import product_events as pe
            from services.product_analytics import track

            track(
                pe.EVENT_DEPLOYMENT_FAILED,
                user_id=user_id,
                project_id=project_id,
                properties={"sample": sample_name, "error": str(e)[:500]},
            )
        except Exception:
            pass
        raise HTTPException(status_code=400, detail=deployment_error(str(e))) from e
    except Exception as e:
        from sqlalchemy.exc import IntegrityError

        if isinstance(e, IntegrityError) or "uq_agent_artifacts" in str(e):
            try:
                from agent_cloud.core.deployments.samples import read_sample_manifest
                from database import deployment_store as _dep_store

                manifest = read_sample_manifest(sample_name)
                active = _dep_store.find_active_deployment(project_id, manifest["name"])
                if active:
                    raise HTTPException(
                        status_code=409,
                        detail=deployment_already_active(active),
                    ) from e
            except HTTPException:
                raise
        try:
            from database import product_events as pe
            from services.product_analytics import track

            track(
                pe.EVENT_DEPLOYMENT_FAILED,
                user_id=user_id,
                project_id=project_id,
                properties={"sample": sample_name, "error": str(e)[:500]},
            )
        except Exception:
            pass
        raise HTTPException(
            status_code=500,
            detail=deployment_error(
                "Sample deploy failed unexpectedly. Check API logs or run alembic upgrade head."
            ),
        ) from e


@router.post("/artifacts/upload")
async def upload_artifact(
    file: UploadFile = File(..., description="ZIP with agent.yaml + agent.py"),
    version: Optional[str] = Form(None, description="Override version from manifest"),
    context: dict = Depends(require_project_can_run),
):
    """Upload and validate agent artifact (Python ZIP)."""
    project_id = context["project_id"]
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail=upload_error("File must be a .zip archive"))
    try:
        data = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read upload: {e}") from e
    try:
        from services.quota_service import check_artifact_upload

        check_artifact_upload(project_id, len(data))
    except QuotaExceeded as e:
        raise HTTPException(status_code=429, detail=quota_error(str(e))) from e
    try:
        artifact = _svc.upload_artifact(project_id, data, version=version)
        return {"artifact": artifact, "message": "Artifact validated"}
    except ValueError as e:
        try:
            from services.product_analytics import track_artifact_upload_failed

            track_artifact_upload_failed(
                project_id,
                user_id=context.get("user", {}).get("id"),
                error=str(e),
            )
        except Exception:
            pass
        raise HTTPException(status_code=400, detail=upload_error(str(e))) from e
    except Exception as e:
        from sqlalchemy.exc import IntegrityError

        if isinstance(e, IntegrityError) or "uq_agent_artifacts" in str(e):
            raise HTTPException(
                status_code=409,
                detail=upload_error(
                    "An artifact with this agent name and version already exists. "
                    "Bump the version in agent.yaml, or deploy the existing artifact."
                ),
            ) from e
        raise


@router.get("/artifacts")
def list_artifacts(
    agent_name: Optional[str] = None,
    context: dict = Depends(require_project_context),
):
    project_id = context["project_id"]
    return {"artifacts": _svc.list_artifacts(project_id, agent_name=agent_name)}


@router.get("/artifacts/{artifact_id}")
def get_artifact(
    artifact_id: uuid.UUID,
    context: dict = Depends(require_project_context),
):
    project_id = context["project_id"]
    art = _svc.get_artifact(project_id, artifact_id)
    if art is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return {"artifact": art}


@router.post("")
def create_deployment(
    body: DeployFromArtifactRequest,
    context: dict = Depends(require_project_can_run),
):
    """Deploy a validated artifact (activates runtime for this project)."""
    project_id = context["project_id"]
    user_id = context.get("user", {}).get("id")
    try:
        aid = uuid.UUID(body.artifact_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid artifact_id") from e
    try:
        from services.quota_service import check_deployment_quota

        check_deployment_quota(project_id)
    except QuotaExceeded as e:
        raise HTTPException(status_code=429, detail=quota_error(str(e))) from e
    try:
        dep = _svc.deploy(project_id, aid, configuration=body.configuration)
        try:
            from services.usage_metering import record_deployment_created

            record_deployment_created(
                project_id,
                uuid.UUID(dep["deployment_id"]),
                artifact_id=aid,
            )
        except Exception:
            pass
        return {"deployment": dep, "message": "Deployment active"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("")
def list_deployments(
    agent_name: Optional[str] = None,
    context: dict = Depends(require_project_context),
):
    project_id = context["project_id"]
    return {"deployments": _svc.list_for_project(project_id, agent_name=agent_name)}


@router.get("/{deployment_id}")
def get_deployment(
    deployment_id: uuid.UUID,
    context: dict = Depends(require_project_context),
):
    project_id = context["project_id"]
    dep = _svc.get(project_id, deployment_id)
    if dep is None:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return {"deployment": dep}


@router.get("/{deployment_id}/health")
def deployment_health(
    deployment_id: uuid.UUID,
    context: dict = Depends(require_project_context),
):
    project_id = context["project_id"]
    if _svc.get(project_id, deployment_id) is None:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return _svc.health(deployment_id)


@router.get("/{deployment_id}/events")
def deployment_events(
    deployment_id: uuid.UUID,
    context: dict = Depends(require_project_context),
):
    project_id = context["project_id"]
    if _svc.get(project_id, deployment_id) is None:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return {"events": _svc.events(deployment_id)}


@router.post("/{deployment_id}/rollback")
def rollback_deployment(
    deployment_id: uuid.UUID,
    context: dict = Depends(require_project_can_run),
):
    project_id = context["project_id"]
    try:
        dep = _svc.rollback(project_id, deployment_id)
        try:
            from database import product_events as pe
            from services.product_analytics import track

            track(
                pe.EVENT_DEPLOYMENT_ROLLBACK,
                user_id=context.get("user", {}).get("id"),
                project_id=project_id,
                deployment_id=deployment_id,
            )
        except Exception:
            pass
        return {"deployment": dep, "message": "Rollback applied"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=deployment_error(str(e))) from e


@router.post("/{deployment_id}/run", response_model=AgentsV2RunResponse)
def run_deployment(
    deployment_id: uuid.UUID,
    body: RunDeploymentRequest,
    context: dict = Depends(require_project_can_run),
):
    """Enqueue a task bound to this deployment's artifact."""
    project_id = context["project_id"]
    dep = _svc.get(project_id, deployment_id)
    if dep is None:
        raise HTTPException(status_code=404, detail="Deployment not found")
    if dep["status"] != "active":
        raise HTTPException(
            status_code=400,
            detail=deployment_error(
                f"Deployment is not active (status={dep['status']})"
            ),
        )
    payload = {
        "task": body.task_text,
        "agent": dep["agent_name"],
        "deployment_id": str(deployment_id),
        "runtime": "deployment",
        "input": body.input,
    }
    try:
        task_id = enqueue_task(payload, project_id=project_id)
    except QuotaExceeded as e:
        raise HTTPException(status_code=429, detail=quota_error(str(e))) from e
    return AgentsV2RunResponse(
        status="task queued",
        task_id=task_id,
        agent=dep["agent_name"],
        task=body.task_text,
    )
