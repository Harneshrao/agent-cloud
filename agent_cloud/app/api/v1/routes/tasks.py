"""Task HTTP surface — thin wrapper over `TaskApplicationService`."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from agent_cloud.app.api.v1.deps import get_task_service
from agent_cloud.contracts.dto.task_dto import TaskEnqueueRequest
from agent_cloud.core.tasks.service import TaskApplicationService

router = APIRouter()


@router.post("/enqueue", status_code=202)
def enqueue_task(
    body: TaskEnqueueRequest,
    svc: TaskApplicationService = Depends(get_task_service),
) -> dict[str, str]:
    tid = svc.enqueue(body)
    return {"task_id": str(tid), "status": "queued"}


@router.get("/{task_id}")
def get_task_stub(task_id: UUID) -> dict:
    """Placeholder — wire `TaskRepository.get` when exposing reads via v1."""
    return {"task_id": str(task_id), "detail": "use legacy API or extend TaskRepository"}
