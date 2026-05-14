"""
Workflow Observability API: inspect workflow progress, analytics, optimization.

GET /workflows/{task_id} - task status, parent, children, retry counts.
Workflow analytics and optimization: metrics, slow nodes, recommendations.
"""

from __future__ import annotations

import json
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from api.deps import require_project_context, require_project_can_run
from api.schemas.task_responses import (
    WorkflowDemoQueuedResponse,
    WorkflowResumeResponse,
)
from database.task_graph import get_workflow_view
from database.db import db
from task_queue.task_queue import enqueue_task
from database.workflow_nodes import get_nodes
from database.workflow_checkpoints import get_all_checkpoints
from engine.stream_store import get_events
from database.workflow_analytics import (
    get_workflow_run_metrics,
    get_aggregate_workflow_metrics,
    get_slow_nodes,
)
from engine.dag_scheduler import resume_workflow
from engine.workflow_optimization import (
    identify_slow_nodes,
    generate_recommendations,
    get_optimization_summary,
    apply_optimization,
)


router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("/{workflow_id}/resume", response_model=WorkflowResumeResponse)
def post_workflow_resume(
    workflow_id: UUID,
    context: dict = Depends(require_project_context),
):
    """
    Resume a workflow after crash/restart. Enqueues nodes that are pending or failed
    and whose dependencies are completed. Requires project context.
    """
    cur = db.get_connection().cursor()
    cur.execute("SELECT id, project_id FROM tasks WHERE id = ?", (str(workflow_id),))
    row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    expected = context["project_id"]
    row_pid = row.get("project_id")
    if row_pid is not None and row_pid != expected:
        raise HTTPException(status_code=403, detail="Access denied to this workflow")
    enqueued = resume_workflow(workflow_id)
    return WorkflowResumeResponse(
        status="resumed",
        workflow_id=workflow_id,
        enqueued_task_ids=enqueued,
    )


@router.post("/demo")
def post_demo_workflow(context: dict = Depends(require_project_can_run)):
    """
    Create and enqueue a demo workflow for the current project.

    Returns the root task_id so the frontend can poll /workflows/{task_id}
    and /tasks/{task_id}/stream for logs/output.
    """
    project_id = context["project_id"]
    payload = {
        # Leave `agent` unset so the orchestrator/router selects a valid pipeline
        # (e.g. research -> execution). This avoids referencing a nonexistent agent.
        "task": "Run demo workflow",
        "agent": None,
        "runtime": "v1",
        "input": {"demo": True, "source": "dashboard"},
    }
    task_id = enqueue_task(payload, project_id=project_id, user_region=None)
    return WorkflowDemoQueuedResponse(status="queued", task_id=task_id)


@router.get("/{task_id}")
def get_workflow(
    task_id: UUID,
    context: dict = Depends(require_project_context),
):
    """
    Return workflow observability for the given task_id.
    Requires Authorization and X-Project-ID (or project_id query).
    Returns 403 if task does not belong to the project.
    """
    view = get_workflow_view(task_id)
    if view is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    project_id = context["project_id"]
    task_project_id = view.get("project_id")
    expected = project_id
    if task_project_id is not None and project_id is not None:
        if task_project_id != expected:
            raise HTTPException(status_code=403, detail="Access denied to this task")
    if task_project_id is None and project_id is not None:
        raise HTTPException(status_code=403, detail="Task is not scoped to this project")

    # Distributed workflows: task_graph may be empty, so fall back to workflow_nodes/checkpoints.
    try:
        nodes = get_nodes(task_id)
    except Exception:
        nodes = []

    if nodes and len(view.get("child_tasks") or []) == 0:
        checkpoints = get_all_checkpoints(task_id)
        cp_by_node_id = {cp["node_id"]: cp for cp in checkpoints}

        cur = db.get_connection().cursor()
        cur.execute("SELECT input_json, status FROM tasks WHERE id = ?", (str(task_id),))
        root_row = cur.fetchone()
        root_status_raw = root_row["status"] if root_row and root_row.get("status") is not None else "running"
        rs = root_status_raw.value if hasattr(root_status_raw, "value") else root_status_raw
        root_status = "running" if str(rs) == "workflow_root" else str(rs)
        ij = root_row.get("input_json") if root_row else None
        if isinstance(ij, dict):
            root_task_text = json.dumps(ij)
        elif ij is None:
            root_task_text = None
        else:
            root_task_text = str(ij)

        child_tasks = []
        for n in nodes:
            node_id = n.get("node_id") or ""
            task_task_id = n.get("task_id")
            task_text = n.get("task_text") or None

            cp = cp_by_node_id.get(node_id)
            node_status = cp.get("status") if cp else n.get("status") or "pending"
            node_output = cp.get("result") if cp else None
            node_logs = get_events(task_task_id) if task_task_id is not None else []

            child_tasks.append(
                {
                    "task_id": str(task_task_id) if task_task_id is not None else None,
                    "task_text": task_text,
                    "status": node_status,
                    "retry_count": 0,
                    # Extra fields for UX (optional; UI may ignore).
                    "node_id": node_id,
                    "output": node_output,
                    "logs": node_logs,
                }
            )

        return {
            "task_id": str(task_id),
            "task_text": root_task_text,
            "status": root_status,
            "parent_task_id": None,
            "retry_count": 0,
            "child_tasks": child_tasks,
        }

    return view


# ---------- Workflow analytics ----------


@router.get("/analytics/run/{workflow_id}")
def get_workflow_run_analytics(
    workflow_id: UUID,
    context: dict = Depends(require_project_context),
):
    """Return metrics for a single workflow run: average_runtime_ms, failure_rate, resource_usage, node_metrics."""
    cur = db.get_connection().cursor()
    cur.execute("SELECT id, project_id FROM tasks WHERE id = ?", (str(workflow_id),))
    row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    expected = context["project_id"]
    if row.get("project_id") is not None and row["project_id"] != expected:
        raise HTTPException(status_code=403, detail="Access denied")
    out = get_workflow_run_metrics(workflow_id)
    if out is None:
        raise HTTPException(status_code=404, detail="No metrics for this workflow run")
    return out


@router.get("/analytics/aggregate")
def get_workflow_aggregate_analytics(
    window_days: int = Query(30, ge=1, le=365),
    template_id: Optional[int] = Query(None),
    context: dict = Depends(require_project_context),
):
    """Aggregate workflow metrics over a time window; optional filter by template_id. Requires project context."""
    return get_aggregate_workflow_metrics(window_days=window_days, template_id=template_id)


# ---------- Workflow optimization ----------


@router.get("/optimization/slow-nodes")
def get_workflow_slow_nodes(
    window_days: int = Query(30, ge=1, le=365),
    min_runs: int = Query(3, ge=1),
    top_n: int = Query(10, ge=1, le=50),
    context: dict = Depends(require_project_context),
):
    """Identify slowest workflow nodes (by agent) for optimization. Requires project context."""
    return {"slow_nodes": identify_slow_nodes(window_days=window_days, min_runs=min_runs, top_n=top_n)}


@router.get("/optimization/recommendations")
def get_workflow_recommendations(
    template_id: Optional[int] = Query(None),
    workflow_id: Optional[int] = Query(None),
    window_days: int = Query(30, ge=1, le=365),
    context: dict = Depends(require_project_context),
):
    """Suggest improvements: parallelize nodes, change agent order, increase worker resources. Requires project context."""
    return {"recommendations": generate_recommendations(template_id=template_id, workflow_id=workflow_id, window_days=window_days)}


@router.get("/optimization/summary")
def get_workflow_optimization_summary(
    template_id: Optional[int] = Query(None),
    window_days: int = Query(30, ge=1, le=365),
    context: dict = Depends(require_project_context),
):
    """Return slow nodes, recommendations, and aggregate metrics for dashboards. Requires project context."""
    return get_optimization_summary(template_id=template_id, window_days=window_days)


@router.post("/optimization/apply")
def post_workflow_optimization_apply(
    template_id: int = Query(..., description="Template to optimize"),
    recommendation_id: str = Query(..., description="Recommendation id from /optimization/recommendations"),
    dry_run: bool = Query(True, description="If true, only report what would change"),
    context: dict = Depends(require_project_context),
):
    """(Optional) Apply a recommendation to a template DAG. dry_run=True only reports what would change. Requires project context."""
    return apply_optimization(template_id=template_id, recommendation_id=recommendation_id, dry_run=dry_run)
