"""Promote scheduled/retry ZSETs + optional visibility recovery."""

from __future__ import annotations

import time

from agent_cloud.infra.redis.scheduler import promote_due
from execution.recovery import requeue_stale_visibility_tasks


def run_promoter_tick(now_ms: int | None = None) -> tuple[list[str], list[str]]:
    now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
    promoted = promote_due(now_ms)
    recovered = requeue_stale_visibility_tasks()
    return promoted, recovered
