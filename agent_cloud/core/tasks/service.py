"""
Task application service — pure orchestration using ports.

API layer and workers obtain a TaskService via dependency injection with concrete
infra repositories wired in `agent_cloud.app.api.v1.deps`.
"""

from __future__ import annotations

from uuid import UUID

from agent_cloud.contracts.dto.task_dto import TaskEnqueueRequest, TaskView
from agent_cloud.core.tasks.models import Task
from agent_cloud.core.tasks.ports import TaskQueuePort, TaskRepository


class TaskApplicationService:
    """Enqueue and claim tasks without knowing about SQL or Redis wire format."""

    def __init__(
        self,
        tasks: TaskRepository,
        queue: TaskQueuePort,
        *,
        default_project_id: UUID,
    ) -> None:
        self._tasks = tasks
        self._queue = queue
        self._default_project_id = default_project_id

    def enqueue(self, body: TaskEnqueueRequest) -> UUID:
        """Create DB row + push to ready queue (scheduled path: extend in infra)."""
        pid = body.project_id or self._default_project_id
        task_id = self._tasks.create_queued(
            body.payload,
            pid,
            idempotency_key=body.idempotency_key,
        )
        self._queue.enqueue_ready(task_id)
        return task_id

    def claim(self, task_id: UUID, worker_id: str | None) -> Task | None:
        return self._tasks.try_claim(task_id, worker_id)

    def complete(self, task_id: UUID, result: dict) -> None:
        self._tasks.mark_completed(task_id, result)

    def to_view(self, task: Task) -> TaskView:
        return TaskView(
            id=task.id,
            project_id=task.project_id,
            status=task.status.value,
            payload=task.payload,
            retries=task.retries,
            max_retries=task.max_retries,
        )
