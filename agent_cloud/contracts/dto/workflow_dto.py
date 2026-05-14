"""Workflow / DAG DTOs."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class WorkflowNodeDTO(BaseModel):
    node_id: str
    agent: str | None = None
    task: str = ""
    deps: list[str] = Field(default_factory=list)


class WorkflowRunRequest(BaseModel):
    template_id: int
    project_id: UUID
    inputs: dict[str, Any] = Field(default_factory=dict)
