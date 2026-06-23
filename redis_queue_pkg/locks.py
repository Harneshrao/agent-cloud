from __future__ import annotations

from typing import Optional, Union

import redis

from config.redis_keys import lock_task_key
from redis_queue_pkg.redis_client import get_redis_client, redis_execute


def _client() -> redis.Redis:
    return get_redis_client()


def acquire_task_lock(task_id: Union[str, int], ttl_s: int = 300) -> bool:
    key = lock_task_key(str(task_id))

    def _acquire(r: redis.Redis) -> bool:
        return bool(r.set(key, "1", nx=True, ex=ttl_s))

    return bool(redis_execute(_acquire))


def release_task_lock(task_id: Union[str, int]) -> None:
    key = lock_task_key(str(task_id))

    def _release(r: redis.Redis) -> None:
        r.delete(key)

    try:
        redis_execute(_release)
    except Exception:
        pass


def try_idempotency_marker(task_id: Union[str, int], ttl_s: int = 86400) -> bool:
    """SET idempotency:{task_id} if not exists. Returns True if acquired."""
    from config.redis_keys import idempotency_key

    k = idempotency_key(str(task_id))

    def _mark(r: redis.Redis) -> bool:
        return bool(r.set(k, "1", nx=True, ex=ttl_s))

    return bool(redis_execute(_mark))
