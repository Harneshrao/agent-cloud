from __future__ import annotations

from typing import Optional, Union

import redis

from config.redis_keys import lock_task_key
from config.settings import REDIS_URL

_redis: Optional[redis.Redis] = None


def _client() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(REDIS_URL, decode_responses=True)
    return _redis


def acquire_task_lock(task_id: Union[str, int], ttl_s: int = 300) -> bool:
    key = lock_task_key(str(task_id))
    return bool(_client().set(key, "1", nx=True, ex=ttl_s))


def release_task_lock(task_id: Union[str, int]) -> None:
    key = lock_task_key(str(task_id))
    _client().delete(key)


def try_idempotency_marker(task_id: Union[str, int], ttl_s: int = 86400) -> bool:
    """SET idempotency:{task_id} if not exists. Returns True if acquired."""
    from config.redis_keys import idempotency_key

    k = idempotency_key(str(task_id))
    return bool(_client().set(k, "1", nx=True, ex=ttl_s))
