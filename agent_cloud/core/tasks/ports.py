"""Ports — infrastructure implemented in agent_cloud.infra.db.repositories."""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from agent_cloud.core.tasks.models import Task


class TaskRepository(Protocol):
    """Persistence boundary for tasks (implemented by Postgres)."""

    def create_queued(
        self,
        payload: dict[str, Any],
        project_id: UUID,
        *,
        idempotency_key: str | None,
    ) -> UUID:
        """Insert task in queued state and return id."""
        ...

    def try_claim(self, task_id: UUID, worker_id: str | None) -> Task | None:
        """Atomic claim: queued|retry|pending → running. None if lost race."""
        ...

    def mark_completed(self, task_id: UUID, result: dict[str, Any]) -> None:
        ...

    def mark_failed(self, task_id: UUID) -> None:
        ...

    def mark_retry(self, task_id: UUID, *, retries: int) -> None:
        ...

    def mark_dead(self, task_id: UUID, reason: str) -> None:
        ...


class TaskQueuePort(Protocol):
    """Redis queue boundary (ready list)."""

    def enqueue_ready(self, task_id: UUID) -> None:
        ...
