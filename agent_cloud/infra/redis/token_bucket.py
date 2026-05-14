"""
Redis token-bucket (distributed). Key: rate:{identity}

Uses HMGET/HSET + refill rate; atomic via Lua for correctness under concurrency.
"""

from __future__ import annotations

import time
from typing import Optional

_TOKEN_BUCKET_LUA = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_per_sec = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local cost = tonumber(ARGV[4])
local ttl = tonumber(ARGV[5])

local data = redis.call('HMGET', key, 'tokens', 'ts')
local tokens = tonumber(data[1])
local ts = tonumber(data[2])

if tokens == nil then
  tokens = capacity
  ts = now
else
  local elapsed = math.max(0, now - ts)
  tokens = math.min(capacity, tokens + elapsed * refill_per_sec)
  ts = now
end

if tokens < cost then
  redis.call('HSET', key, 'tokens', tokens, 'ts', ts)
  redis.call('EXPIRE', key, ttl)
  return 0
end

tokens = tokens - cost
redis.call('HSET', key, 'tokens', tokens, 'ts', ts)
redis.call('EXPIRE', key, ttl)
return 1
"""


def allow(
    redis_client: object,
    key: str,
    *,
    capacity: float,
    refill_per_sec: float,
    cost: float = 1.0,
    ttl_sec: int = 3600,
) -> bool:
    """
    Returns True if request is allowed. On Redis errors, returns True (fail-open).
    """
    now = time.time()
    try:
        ok = redis_client.eval(  # type: ignore[union-attr]
            _TOKEN_BUCKET_LUA,
            1,
            key,
            str(capacity),
            str(refill_per_sec),
            str(now),
            str(cost),
            str(ttl_sec),
        )
        return int(ok) == 1
    except Exception:
        return True


def rate_user_key(user_sub: str) -> str:
    return f"rate:{user_sub}"
