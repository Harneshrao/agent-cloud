"""TaskApplicationService with in-memory ports."""

from __future__ import annotations

from uuid import UUID, uuid4

from agent_cloud.contracts.dto.task_dto import TaskEnqueueRequest
from agent_cloud.core.tasks.models import Task
from agent_cloud.core.tasks.ports import TaskQueuePort, TaskRepository
from agent_cloud.core.tasks.service import TaskApplicationService


class FakeQueue(TaskQueuePort):
    def __init__(self) -> None:
        self.ids: list[UUID] = []

    def enqueue_ready(self, task_id: UUID) -> None:
        self.ids.append(task_id)


class FakeRepo(TaskRepository):
    def __init__(self) -> None:
        self.created: list[tuple[dict, UUID, str | None]] = []

    def create_queued(
        self,
        payload: dict,
        project_id: UUID,
        *,
        idempotency_key: str | None,
    ) -> UUID:
        tid = uuid4()
        self.created.append((payload, project_id, idempotency_key))
        return tid

    def try_claim(
        self, task_id: UUID, worker_id: str | None
    ) -> Task | None:
        return None

    def mark_completed(self, task_id: UUID, result: dict) -> None:
        pass

    def mark_failed(self, task_id: UUID) -> None:
        pass

    def mark_retry(self, task_id: UUID, *, retries: int) -> None:
        pass

    def mark_dead(self, task_id: UUID, reason: str) -> None:
        pass


def test_enqueue_calls_queue() -> None:
    q = FakeQueue()
    r = FakeRepo()
    pid = uuid4()
    svc = TaskApplicationService(r, q, default_project_id=pid)
    body = TaskEnqueueRequest(payload={"task": "hello"}, project_id=None)
    tid = svc.enqueue(body)
    assert q.ids == [tid]
    assert r.created[0][0] == {"task": "hello"}
    assert r.created[0][1] == pid


if __name__ == "__main__":
    test_enqueue_calls_queue()
    print("ok")
