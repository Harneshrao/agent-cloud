"""
Shared API response models for task identifiers (PostgreSQL UUID primary keys).

OpenAPI: `task_id` and `task_ids` use `format: uuid` (JSON strings).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TaskQueuedResponse(BaseModel):
    """Generic enqueue response with a single task id."""

    model_config = ConfigDict(json_schema_extra={"example": {"status": "queued", "task_id": "2f27ff16-1b2a-4dfc-9a3f-a02e12182105"}})

    status: str = Field(..., description="Human-readable status")
    task_id: UUID = Field(..., description="Primary key of the tasks row")


class WorkflowDemoQueuedResponse(BaseModel):
    status: str
    task_id: UUID


class WorkflowResumeResponse(BaseModel):
    status: str
    workflow_id: UUID = Field(
        ...,
        description="Root workflow task id (tasks.id); matches workflow_nodes.workflow_id",
    )
    enqueued_task_ids: list[UUID] = Field(
        default_factory=list,
        description="Newly enqueued node task ids from resume",
    )


class AgentsV2RunResponse(BaseModel):
    status: str
    task_id: UUID
    agent: str
    task: str


class MarketplaceAgentRunResponse(BaseModel):
    status: str
    agent: str
    task_id: UUID
    project_id: UUID = Field(..., description="Project scope (projects.id)")


class InstallationRunResponse(BaseModel):
    message: str
    task_id: UUID
    installation_id: int
    agent_name: str


class ProductInstallationRunResponse(BaseModel):
    message: str
    task_id: UUID
    installation_id: int
    agent_name: str


class AgentInstanceRunResponse(BaseModel):
    status: str
    task_id: UUID
    agent_instance_id: str
    agent_name: str | None
    task: str


class AgentInstanceAutonomousCycleResponse(BaseModel):
    status: str
    agent_instance_id: str
    tasks_queued: int
    task_ids: list[UUID]


class EventIngestResponse(BaseModel):
    """POST /events — production tasks enqueued from triggers (UUID ids)."""

    status: str
    event_type: str
    tasks_queued: int
    task_ids: list[UUID]
    project_id: UUID


class WebhookIngestResponse(BaseModel):
    """POST /webhooks/{source} — production tasks enqueued (UUID ids)."""

    status: str
    source: str
    event_type: str
    tasks_queued: int
    task_ids: list[UUID]


class SimulationProcessEventsResponse(BaseModel):
    """POST /simulations/{id}/process-events — simulation_tasks use integer ids."""

    tasks_queued: int
    task_ids: list[int] = Field(..., description="simulation_tasks.id values")
    simulation: dict[str, Any] = Field(default_factory=dict)


class TemplateRunResponse(BaseModel):
    """POST /templates/{id}/run — distributed and non-distributed paths."""

    status: str
    template_id: int
    project_id: UUID
    version: str | None = None
    inputs: dict[str, Any] | None = None
    distributed: bool | None = None
    workflow_id: UUID | None = Field(None, description="Set when distributed=True")
    root_task_ids: list[UUID] = Field(default_factory=list)
    task_ids: list[UUID] | None = Field(
        None, description="All node task ids (non-distributed); omitted when distributed-only payload"
    )


class DemoWorkflowStartResponse(BaseModel):
    workflow_id: UUID = Field(..., description="Root workflow task id")

