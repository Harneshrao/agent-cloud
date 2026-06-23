"""
Hardened Redis client for Windows Docker + local dev.

- Prefer 127.0.0.1 over localhost on Windows (resolver/socket reset issues).
- Auto-reconnect with backoff on connection resets.
- Never leave the worker process down on transient Redis errors.
"""

from __future__ import annotations

import logging
import sys
import time
from typing import Callable, Optional, TypeVar

import redis
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

logger = logging.getLogger(__name__)

T = TypeVar("T")

_backoff_sec = 1.0
_max_backoff_sec = 5.0
_client: Optional[redis.Redis] = None

_REDIS_TRANSIENT = (
    RedisConnectionError,
    RedisTimeoutError,
    ConnectionResetError,
    BrokenPipeError,
    OSError,
)


def normalize_redis_url(url: str) -> str:
    """Use numeric loopback on Windows to avoid localhost socket resets."""
    if sys.platform != "win32":
        return url
    out = url
    for host in ("localhost", "127.0.0.1"):
        pass
    out = out.replace("redis://localhost:", "redis://127.0.0.1:")
    out = out.replace("@localhost:", "@127.0.0.1:")
    if out.endswith("redis://localhost"):
        out = out.replace("redis://localhost", "redis://127.0.0.1")
    return out


def make_redis_client(url: Optional[str] = None) -> redis.Redis:
    from config.settings import REDIS_URL

    raw = normalize_redis_url(url or REDIS_URL)
    return redis.from_url(
        raw,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=30,
        retry_on_timeout=True,
        health_check_interval=15,
        socket_keepalive=True,
    )


def invalidate_task_queue_cache() -> None:
    """Drop cached TaskQueue so it binds to a fresh client."""
    try:
        from redis_queue_pkg import redis_queue as rq

        rq._queue = None  # type: ignore[attr-defined]
        rq._redis = None  # type: ignore[attr-defined]
    except Exception:
        pass
    try:
        from redis_queue_pkg import locks as locks_mod

        locks_mod._redis = None  # type: ignore[attr-defined]
    except Exception:
        pass


def reset_redis_client() -> redis.Redis:
    """Close and recreate the global client after a disconnect."""
    global _client, _backoff_sec
    logger.warning("Redis disconnected")
    if _client is not None:
        try:
            _client.close()
        except Exception:
            pass
    sleep_s = min(_backoff_sec, _max_backoff_sec)
    time.sleep(sleep_s)
    _backoff_sec = min(_backoff_sec * 2, _max_backoff_sec)
    _client = make_redis_client()
    invalidate_task_queue_cache()
    logger.info("Redis reconnect successful")
    return _client


def get_redis_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = make_redis_client()
    return _client


def note_redis_success() -> None:
    """Reset backoff after a successful operation."""
    global _backoff_sec
    _backoff_sec = 1.0


def redis_execute(
    op: Callable[[redis.Redis], T],
    *,
    max_attempts: int = 5,
    on_reconnect: Optional[Callable[[], None]] = None,
) -> T:
    """
    Run ``op(client)`` with automatic reconnect on transient failures.
    """
    global _client
    last_exc: Optional[BaseException] = None
    for attempt in range(1, max_attempts + 1):
        try:
            client = get_redis_client()
            result = op(client)
            note_redis_success()
            return result
        except _REDIS_TRANSIENT as exc:
            last_exc = exc
            logger.warning(
                "Redis operation failed (attempt %s/%s): %s",
                attempt,
                max_attempts,
                exc,
            )
            _client = reset_redis_client()
            if on_reconnect is not None:
                try:
                    on_reconnect()
                except Exception:
                    logger.exception("on_reconnect hook failed")
    assert last_exc is not None
    raise last_exc


def redis_ping() -> bool:
    try:
        redis_execute(lambda r: r.ping())
        return True
    except Exception:
        return False


def worker_heartbeat_key(worker_id: str) -> str:
    return f"workers:{worker_id}:heartbeat"


def write_worker_redis_heartbeat(
    worker_id: str,
    *,
    tasks_running: int = 0,
    ttl_sec: int = 60,
) -> None:
    """Fast liveness signal for dev_doctor / dashboard (survives brief PG blips)."""
    import json

    payload = json.dumps(
        {"worker_id": worker_id, "tasks_running": tasks_running, "ts": int(time.time())}
    )

    def _set(r: redis.Redis) -> None:
        r.set(worker_heartbeat_key(worker_id), payload, ex=ttl_sec)

    redis_execute(_set)


def any_worker_redis_heartbeat(within_sec: int = 60) -> tuple[bool, str]:
    """True if any workers:*:heartbeat key exists with TTL > 0."""
    _ = within_sec  # keys use ex=60; TTL presence is sufficient

    def _scan(r: redis.Redis) -> tuple[bool, str]:
        for key in r.scan_iter(match="workers:*:heartbeat", count=50):
            ttl = r.ttl(key)
            if ttl is not None and ttl > 0:
                return True, str(key)
        return False, "no redis worker heartbeat keys"

    try:
        return redis_execute(_scan)
    except Exception as exc:
        return False, str(exc)[:120]
