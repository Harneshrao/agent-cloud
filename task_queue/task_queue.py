"""Shim: re-exports from services (legacy import path `task_queue.task_queue`)."""

from services.task_payload import parse_payload as _parse_payload
from services.task_service import (
    enqueue_task,
    fetch_next_task,
    push_existing_task,
    update_task_status,
    update_task_heartbeat,
)

__all__ = [
    "enqueue_task",
    "fetch_next_task",
    "push_existing_task",
    "update_task_status",
    "update_task_heartbeat",
    "_parse_payload",
]
