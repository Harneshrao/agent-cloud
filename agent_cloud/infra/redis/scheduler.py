"""ZSET promotion (scheduled / retry) — delegates to TaskQueue."""

from __future__ import annotations

from redis_queue_pkg.redis_queue import get_task_queue


def promote_due(now_ms: int, batch: int = 500) -> list[str]:
    return get_task_queue().promote_scheduled_and_retry(now_ms, batch=batch)
