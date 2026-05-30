"""Operational correlation fields (API → worker → logs → task_events)."""

from __future__ import annotations

import uuid
from contextvars import ContextVar, Token
from typing import Any, Optional

from agent_cloud.infra.observability.context import get_trace_id, set_trace_id

_execution_id: ContextVar[Optional[str]] = ContextVar("execution_id", default=None)
_task_id: ContextVar[Optional[str]] = ContextVar("op_task_id", default=None)
_project_id: ContextVar[Optional[str]] = ContextVar("op_project_id", default=None)
_deployment_id: ContextVar[Optional[str]] = ContextVar("op_deployment_id", default=None)
_worker_id: ContextVar[Optional[str]] = ContextVar("op_worker_id", default=None)
_queue_name: ContextVar[Optional[str]] = ContextVar("op_queue_name", default=None)
_retry_count: ContextVar[Optional[int]] = ContextVar("op_retry_count", default=None)
_runtime_version: ContextVar[Optional[str]] = ContextVar("op_runtime_version", default=None)


def bind_execution(
    *,
    task_id: str | uuid.UUID | None = None,
    project_id: str | uuid.UUID | None = None,
    deployment_id: str | uuid.UUID | None = None,
    worker_id: str | None = None,
    queue_name: str | None = None,
    retry_count: int | None = None,
    runtime_version: str | None = None,
    execution_id: str | None = None,
    trace_id: str | None = None,
) -> Token[Any]:
    """Bind operational fields; returns trace token for reset."""
    if task_id is not None:
        _task_id.set(str(task_id))
    if project_id is not None:
        _project_id.set(str(project_id))
    if deployment_id is not None:
        _deployment_id.set(str(deployment_id))
    if worker_id is not None:
        _worker_id.set(worker_id)
    elif not _worker_id.get():
        import os

        wid = os.environ.get("WORKER_ID", "").strip()
        if wid:
            _worker_id.set(wid)
    if queue_name is not None:
        _queue_name.set(queue_name)
    if retry_count is not None:
        _retry_count.set(retry_count)
    if runtime_version is not None:
        _runtime_version.set(runtime_version)
    if execution_id is not None:
        _execution_id.set(execution_id)
    else:
        _execution_id.set(str(uuid.uuid4()))
    return set_trace_id(trace_id or (str(task_id) if task_id else None))


def snapshot() -> dict[str, Any]:
    """Current operational context as a dict (for logs and events)."""
    return {
        "trace_id": get_trace_id(),
        "execution_id": _execution_id.get(),
        "task_id": _task_id.get(),
        "project_id": _project_id.get(),
        "deployment_id": _deployment_id.get(),
        "worker_id": _worker_id.get(),
        "queue_name": _queue_name.get(),
        "retry_count": _retry_count.get(),
        "runtime_version": _runtime_version.get(),
    }


def clear_execution(token: Token[Any]) -> None:
    from agent_cloud.infra.observability.context import reset_trace_id

    reset_trace_id(token)
