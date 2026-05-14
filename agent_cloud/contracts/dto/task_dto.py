"""Task DTOs — boundary between HTTP, workers, and domain."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class TaskEnqueueRequest(BaseModel):
    """API / worker input for creating work."""

    payload: dict[str, Any] = Field(default_factory=dict)
    project_id: UUID | None = None
    idempotency_key: str | None = Field(None, max_length=512)
    scheduled_at: datetime | None = None


class TaskView(BaseModel):
    """Read model returned to API after persistence."""

    id: UUID
    project_id: UUID
    status: str
    payload: dict[str, Any]
    result: dict[str, Any] | None = None
    retries: int = 0
    max_retries: int = 3
    worker_id: str | None = None
    created_at: datetime | None = None
