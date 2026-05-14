"""Compatibility exports — use `services.task_service` and `redis_queue_pkg.redis_queue` in new code."""

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
