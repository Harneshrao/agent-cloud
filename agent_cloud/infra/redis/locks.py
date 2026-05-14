"""Distributed locks — thin wrapper over redis_queue_pkg.locks."""

from __future__ import annotations

from redis_queue_pkg.locks import acquire_task_lock, release_task_lock

__all__ = ["acquire_task_lock", "release_task_lock"]
