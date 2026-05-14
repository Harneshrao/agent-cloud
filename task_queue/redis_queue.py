"""Shim: Redis queue helpers (legacy path `task_queue.redis_queue`)."""

from __future__ import annotations

from typing import List, Optional

from redis_queue_pkg.redis_queue import (
    TASKS_QUEUE_KEY,
    TaskQueue,
    get_task_queue,
    _get_redis_queue_length,
)
from services.task_service import enqueue_task, fetch_next_task, push_existing_task


def _task_satisfies_capabilities(
    required: Optional[List[str]], worker_caps: Optional[List[str]]
) -> bool:
    if not required:
        return True
    if worker_caps is None:
        return True
    return all(r in worker_caps for r in required)


__all__ = [
    "TASKS_QUEUE_KEY",
    "TaskQueue",
    "get_task_queue",
    "_get_redis_queue_length",
    "enqueue_task",
    "push_existing_task",
    "fetch_next_task",
    "_task_satisfies_capabilities",
]
