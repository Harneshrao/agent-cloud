"""HTTP request bodies (grouped for OpenAPI generation)."""

from __future__ import annotations

from agent_cloud.contracts.dto.task_dto import TaskEnqueueRequest
from agent_cloud.contracts.dto.workflow_dto import WorkflowRunRequest

__all__ = ["TaskEnqueueRequest", "WorkflowRunRequest"]
