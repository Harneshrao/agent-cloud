"""
Central task scheduler API: workers request the next task from the scheduler.

GET /scheduler/task?worker_id=...&worker_capabilities=...
Returns the best matching task or 204 No Content. Workers fall back to
pulling from the queue directly if the scheduler is unavailable.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, Response

from engine.task_scheduler import get_next_task


router = APIRouter(prefix="/scheduler", tags=["task-scheduler"])


@router.get("/task")
def scheduler_get_task(
    worker_id: str = Query(..., description="Worker identifier"),
    worker_capabilities: Optional[str] = Query(
        None,
        description="Comma-separated capabilities (e.g. python,gpu,browser)",
    ),
    worker_region: Optional[str] = Query(
        None,
        description="Worker region (e.g. us, eu, asia); used to match task target_region",
    ),
    worker_type: Optional[str] = Query(
        None,
        description="Worker type (e.g. edge); edge workers get only edge_compatible agent tasks",
    ),
):
    """
    Return the next task for this worker. Selection: worker_type match (edge vs cloud),
    region match, capability compatibility, then priority and task age. Returns 200 with
    task payload or 204 when no matching task is available.
    """
    caps: Optional[List[str]] = None
    if worker_capabilities:
        caps = [c.strip() for c in worker_capabilities.split(",") if c.strip()]
    region = worker_region.strip() if worker_region and worker_region.strip() else None
    if not region:
        try:
            from database.workers import get_worker_region
            region = get_worker_region(worker_id)
        except Exception:
            pass
    wtype = worker_type.strip().lower() if worker_type and worker_type.strip() else None
    if not wtype:
        try:
            from engine.worker_registry import get_worker_type
            wtype = get_worker_type(worker_id)
        except Exception:
            pass
    task = get_next_task(worker_id=worker_id, worker_capabilities=caps, worker_region=region, worker_type=wtype)
    if task is None:
        return Response(status_code=204)
    return JSONResponse(content=task)
