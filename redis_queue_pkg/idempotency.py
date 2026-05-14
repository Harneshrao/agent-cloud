"""Redis idempotency helpers (key: idempotency:{task_id})."""

from __future__ import annotations

from typing import Union

import redis

from config.redis_keys import idempotency_key
from config.settings import REDIS_URL

_client: redis.Redis | None = None


def _r() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(REDIS_URL, decode_responses=True)
    return _client


def mark_once(task_id: Union[str, int], value: str = "1", ttl_s: int = 86400) -> bool:
    """Returns True if this process was first to set the marker."""
    return bool(_r().set(idempotency_key(str(task_id)), value, nx=True, ex=ttl_s))


def clear(task_id: Union[str, int]) -> None:
    _r().delete(idempotency_key(str(task_id)))
