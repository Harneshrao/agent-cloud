"""Stuck-task recovery: visibility timeouts in Redis + Postgres reconciliation."""

from __future__ import annotations

import time
import uuid

from database.db import db
from redis_queue_pkg.redis_queue import get_task_queue


def requeue_stale_visibility_tasks(batch: int = 100) -> list[str]:
    """
    Pop task ids from queue:processing past deadline; mark Postgres queued and LPUSH ready.
    """
    now_ms = int(time.time() * 1000)
    q = get_task_queue()
    ids = q.pop_stale_processing(now_ms, batch=batch)
    out: list[str] = []
    for raw in ids:
        try:
            tid = uuid.UUID(str(raw))
        except ValueError:
            continue
        db.reset_task_to_pending(tid)
        q.enqueue_ready(tid)
        out.append(str(tid))
    return out
