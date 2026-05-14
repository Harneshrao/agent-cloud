"""
Event API: ingest events and manage event triggers.

POST /events        - Ingest an event; matching triggers enqueue tasks (requires project context).
POST /events/triggers - Register an event trigger (optional).
GET  /events/triggers - List all triggers.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.deps import require_project_context
from api.schemas.task_responses import EventIngestResponse
from database.event_triggers import create, get_by_id, list_all, set_enabled
from engine.event_engine import process_event
from engine.quota_checker import check_quota


router = APIRouter(prefix="/events", tags=["events"])


class IngestEventRequest(BaseModel):
    """Request body for POST /events."""

    event_type: str = Field(..., description="Event type (e.g. new_dataset_uploaded)")
    payload: dict = Field(default_factory=dict, description="Event payload for task_template substitution")


class CreateTriggerRequest(BaseModel):
    """Request body for POST /events/triggers."""

    event_type: str = Field(..., description="Event type to match")
    task_template: str = Field(
        ...,
        description="Task text template; use {{key}} for payload substitution",
    )
    agent: str | None = Field(None, description="Agent to run (optional)")
    enabled: bool = Field(True, description="Whether the trigger is enabled")
    project_id: uuid.UUID | None = Field(None, description="Scope to project (optional)")
    source: str = Field("any", description="Trigger only for this source: user | agent | any")


@router.post("", response_model=EventIngestResponse)
def ingest_event(
    data: IngestEventRequest,
    context: dict = Depends(require_project_context),
):
    """
    Ingest an event. Enabled triggers with matching event_type will run;
    task text is generated from task_template, then tasks are enqueued for the project.
    Requires Authorization and X-Project-ID (or project_id query).
    """
    project_id = context["project_id"]
    check_quota(project_id)
    task_ids = process_event(data.event_type, data.payload, project_id=project_id)
    return EventIngestResponse(
        status="accepted",
        event_type=data.event_type,
        tasks_queued=len(task_ids),
        task_ids=task_ids,
        project_id=project_id,
    )


@router.post("/triggers")
def create_trigger(
    data: CreateTriggerRequest,
    context: dict = Depends(require_project_context),
):
    """Register an event trigger. Optional project_id and source (user|agent|any) for agent-triggered workflows."""
    project_id = context.get("project_id")
    trigger = create(
        event_type=data.event_type,
        task_template=data.task_template,
        agent=data.agent,
        enabled=data.enabled,
        project_id=data.project_id or project_id,
        source=data.source,
    )
    return {"status": "created", "trigger": trigger}


@router.get("/triggers")
def list_triggers(context: dict = Depends(require_project_context)):
    """List event triggers, optionally scoped to project."""
    project_id = context.get("project_id")
    triggers = list_all(project_id=project_id)
    return {"triggers": triggers}


@router.delete("/triggers/{trigger_id}")
def disable_trigger(
    trigger_id: int,
    context: dict = Depends(require_project_context),
):
    """Disable an event trigger by id. Caller must have access to the trigger's project."""
    trigger = get_by_id(trigger_id)
    if trigger is None:
        raise HTTPException(status_code=404, detail=f"Trigger {trigger_id} not found")
    project_id = context["project_id"]
    trigger_project = trigger.get("project_id")
    if trigger_project is not None and trigger_project != project_id:
        raise HTTPException(status_code=403, detail="Access denied to this trigger")
    set_enabled(trigger_id, False)
    return {"status": "disabled", "id": trigger_id}
