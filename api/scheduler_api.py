"""
Scheduler API: create, list, and disable scheduled tasks.

POST /schedule       - Create a scheduled task (requires project context).
GET  /schedule       - List schedules for the project.
DELETE /schedule/{id} - Disable a schedule (requires project access; schedule must belong to project).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.deps import require_project_context
from database.scheduled_tasks import create, get_by_id, list_all, set_enabled
from engine.quota_checker import check_quota


router = APIRouter(tags=["scheduler"])


class CreateScheduleRequest(BaseModel):
    """Request body for POST /schedule."""

    agent: str | None = Field(None, description="Agent name (optional)")
    task_text: str = Field(..., description="Task text to run")
    cron_expression: str = Field(
        ...,
        description="Cron expression (e.g. '0 * * * *' for every hour)",
    )
    enabled: bool = Field(True, description="Whether the schedule is enabled")


@router.post("/schedule")
def create_schedule(
    data: CreateScheduleRequest,
    context: dict = Depends(require_project_context),
):
    """Create a scheduled task for the project. Requires Authorization and X-Project-ID (or project_id query)."""
    project_id = context["project_id"]
    check_quota(project_id)
    schedule = create(
        agent=data.agent,
        task_text=data.task_text,
        cron_expression=data.cron_expression,
        enabled=data.enabled,
        project_id=project_id,
    )
    return {"status": "created", "schedule": schedule, "project_id": project_id}


@router.get("/schedule")
def list_schedules(context: dict = Depends(require_project_context)):
    """List scheduled tasks for the project. Requires Authorization and X-Project-ID (or project_id query)."""
    project_id = context["project_id"]
    schedules = list_all(project_id=project_id)
    return {"schedules": schedules, "project_id": project_id}


@router.delete("/schedule/{schedule_id}")
def disable_schedule(
    schedule_id: int,
    context: dict = Depends(require_project_context),
):
    """Disable a schedule. Schedule must belong to the project."""
    schedule = get_by_id(schedule_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")
    project_id = context["project_id"]
    schedule_project_id = schedule.get("project_id")
    if schedule_project_id is not None and schedule_project_id != project_id:
        raise HTTPException(status_code=403, detail="Access denied to this schedule")
    set_enabled(schedule_id, False)
    return {"status": "disabled", "id": schedule_id, "project_id": project_id}
