"""Singleton Redis client (decode_responses=True)."""

from __future__ import annotations

from typing import Optional

import redis

from agent_cloud.infra.config import settings

_redis: Optional[redis.Redis] = None


def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis
