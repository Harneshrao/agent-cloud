"""Domain models (not ORM)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from agent_cloud.core.tasks.enums import TaskLifecycle


@dataclass(frozen=True, slots=True)
class Task:
    id: UUID
    project_id: UUID
    status: TaskLifecycle
    payload: dict[str, Any]
    retries: int
    max_retries: int
