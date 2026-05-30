"""
Operational visibility API — project-scoped debugging without admin.

Prefix: /observability
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from api.deps import require_project_context
from database.task_observability import (
    build_task_trace,
    list_dlq_for_project,
    list_tasks_for_project,
    queue_snapshot,
    task_counts_for_project,
)
from engine.stream_store import get_events as stream_events
from services.observability_service import (
    assert_task_in_project,
    classify_incidents,
    get_deployment_timeline,
    get_platform_health,
)
from database.workers import get_all_workers

router = APIRouter(prefix="/observability", tags=["observability"])


@router.get("/health")
def observability_health(context: dict = Depends(require_project_context)):
    """Platform + project task stats (lightweight)."""
    project_id = context["project_id"]
    return {
        "platform": get_platform_health(),
        "project": task_counts_for_project(project_id, hours=24),
        "queue": queue_snapshot(),
    }


@router.get("/queue")
def observability_queue(context: dict = Depends(require_project_context)):
    return {"queue": queue_snapshot()}


@router.get("/workers")
def observability_workers(context: dict = Depends(require_project_context)):
    workers = get_all_workers()
    return {"workers": workers, "count": len(workers)}


@router.get("/tasks")
def observability_tasks(
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    context: dict = Depends(require_project_context),
):
    project_id = context["project_id"]
    return {
        "tasks": list_tasks_for_project(project_id, limit=limit, status=status)
    }


@router.get("/tasks/{task_id}")
def observability_task(
    task_id: uuid.UUID,
    context: dict = Depends(require_project_context),
):
    project_id = context["project_id"]
    try:
        detail = assert_task_in_project(task_id, project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    from database.task_observability import list_agent_runs_for_task

    return {
        "task": detail,
        "runs": list_agent_runs_for_task(task_id),
        "stream_events": stream_events(task_id),
    }


@router.get("/tasks/{task_id}/trace")
def observability_task_trace(
    task_id: uuid.UUID,
    context: dict = Depends(require_project_context),
):
    project_id = context["project_id"]
    try:
        assert_task_in_project(task_id, project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    trace = build_task_trace(task_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Task not found")
    return trace


@router.get("/tasks/{task_id}/logs")
def observability_task_logs(
    task_id: uuid.UUID,
    context: dict = Depends(require_project_context),
):
    project_id = context["project_id"]
    try:
        assert_task_in_project(task_id, project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    from database.task_observability import list_task_logs

    return {"logs": list_task_logs(task_id)}


@router.get("/dlq")
def observability_dlq(
    limit: int = Query(50, ge=1, le=200),
    context: dict = Depends(require_project_context),
):
    project_id = context["project_id"]
    items = list_dlq_for_project(project_id, limit=limit)
    return {"dead_letters": items, "count": len(items)}


@router.get("/incidents")
def observability_incidents(context: dict = Depends(require_project_context)):
    project_id = context["project_id"]
    q = queue_snapshot()
    stats = task_counts_for_project(project_id, hours=1)
    return {"incidents": classify_incidents(q, stats)}


@router.get("/deployments/{deployment_id}/timeline")
def observability_deployment_timeline(
    deployment_id: uuid.UUID,
    context: dict = Depends(require_project_context),
):
    project_id = context["project_id"]
    try:
        return get_deployment_timeline(project_id, deployment_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
