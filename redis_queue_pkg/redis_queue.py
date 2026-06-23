"""
Redis-backed task queue — canonical keys from config.redis_keys.

Runnable work: task_id strings (integer string legacy or UUID) on LIST queue:tasks.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Callable, List, Optional, TypeVar, Union

import redis

from config.redis_keys import (
    REDIS_QUEUE_DEAD,
    REDIS_QUEUE_PROCESSING,
    REDIS_QUEUE_RETRY,
    REDIS_QUEUE_SCHEDULED,
    REDIS_QUEUE_TASKS,
)
from config.settings import DEFAULT_BLOCK_TIMEOUT, REDIS_URL
from redis_queue_pkg.redis_client import (
    get_redis_client,
    invalidate_task_queue_cache,
    redis_execute,
    reset_redis_client,
)

logger = logging.getLogger(__name__)

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I
)

_redis: Optional[redis.Redis] = None
_queue: Optional["TaskQueue"] = None

T = TypeVar("T")


def _get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = get_redis_client()
    return _redis


def _queue_op(op: Callable[[redis.Redis], T]) -> T:
    return redis_execute(lambda _: op(_get_redis()))


class TaskQueue:
    """LIST queue:ready, ZSET scheduled/retry/processing, LIST dead."""

    def __init__(self, r: redis.Redis) -> None:
        self.r = r
        self.ready = REDIS_QUEUE_TASKS
        self.dead = REDIS_QUEUE_DEAD
        self.delayed = REDIS_QUEUE_SCHEDULED
        self.retry = REDIS_QUEUE_RETRY
        self.processing = REDIS_QUEUE_PROCESSING

    PROMOTE_LUA = """
    local zkey = KEYS[1]
    local ready = KEYS[2]
    local now = tonumber(ARGV[1])
    local batch = tonumber(ARGV[2])
    local ids = redis.call('ZRANGEBYSCORE', zkey, '-inf', now, 'LIMIT', 0, batch)
    if #ids == 0 then return {} end
    for _, id in ipairs(ids) do
      redis.call('ZREM', zkey, id)
      redis.call('LPUSH', ready, id)
    end
    return ids
    """

    def _run(self, op: Callable[[redis.Redis], T]) -> T:
        return _queue_op(op)

    def enqueue_ready(self, task_id: Union[str, int]) -> None:
        self._run(lambda r: r.lpush(self.ready, str(task_id)))

    def dequeue_blocking(self, timeout_s: int) -> Optional[str]:
        """
        BRPOP with reconnect. Returns None on timeout or after a Redis reset
        (caller should continue the worker loop).
        """
        try:

            def _brpop(r: redis.Redis) -> Optional[str]:
                item = r.brpop(self.ready, timeout=timeout_s)
                if not item:
                    return None
                return item[1]

            return self._run(_brpop)
        except Exception as exc:
            logger.warning("dequeue_blocking redis error: %s", exc)
            try:
                reset_redis_client()
                invalidate_task_queue_cache()
                global _redis, _queue
                _redis = get_redis_client()
                self.r = _redis
            except Exception:
                logger.exception("dequeue_blocking reconnect failed")
            return None

    def dequeue_raw_blocking(self, timeout_s: int) -> Optional[str]:
        return self.dequeue_blocking(timeout_s)

    def lpush_raw(self, raw: str) -> None:
        self._run(lambda r: r.lpush(self.ready, raw))

    def schedule_delayed(self, task_id: Union[str, int], run_at_ms: int) -> None:
        self._run(lambda r: r.zadd(self.delayed, {str(task_id): run_at_ms}))

    def schedule_retry(self, task_id: Union[str, int], run_at_ms: int) -> None:
        self._run(lambda r: r.zadd(self.retry, {str(task_id): run_at_ms}))

    def promote_due_from_zset(self, zset_key: str, now_ms: int, batch: int = 100) -> List[str]:
        def _promote(r: redis.Redis) -> List[str]:
            out = r.eval(self.PROMOTE_LUA, 2, zset_key, self.ready, str(now_ms), str(batch))
            return [str(x) for x in (out or [])]

        return self._run(_promote)

    def promote_scheduled_and_retry(self, now_ms: int, batch: int = 100) -> List[str]:
        ids: List[str] = []
        for zkey in (self.delayed, self.retry):
            ids.extend(self.promote_due_from_zset(zkey, now_ms, batch))
        return ids

    def promote_delayed_and_retries(self, now_ms: int, batch: int = 100) -> List[str]:
        """Alias matching older scheduler name."""
        return self.promote_scheduled_and_retry(now_ms, batch)

    def add_processing(self, task_id: Union[str, int], deadline_ms: int) -> None:
        """Visibility timeout: score = deadline (epoch ms)."""
        self._run(lambda r: r.zadd(self.processing, {str(task_id): float(deadline_ms)}))

    def remove_processing(self, task_id: Union[str, int]) -> None:
        self._run(lambda r: r.zrem(self.processing, str(task_id)))

    def pop_stale_processing(self, now_ms: int, batch: int = 100) -> List[str]:
        """Tasks whose visibility deadline has passed (for recovery / requeue)."""

        def _pop(r: redis.Redis) -> List[str]:
            ids = r.zrangebyscore(self.processing, "-inf", now_ms, start=0, num=batch)
            out = [str(x) for x in ids]
            for x in out:
                r.zrem(self.processing, x)
            return out

        return self._run(_pop)

    def to_dead_letter(
        self, task_id: Union[str, int], error: str, ts_ms: Optional[int] = None
    ) -> None:
        ts_ms = ts_ms or int(time.time() * 1000)
        payload = json.dumps({"task_id": str(task_id), "error": error, "ts_ms": ts_ms})

        def _dlq(r: redis.Redis) -> None:
            r.rpush(self.dead, payload)

        self._run(_dlq)

    def increment_requeue_count(self, task_id: Union[str, int]) -> int:
        """Track hot-loop requeues; expire after 1h."""
        key = f"queue:requeue_count:{task_id}"

        def _incr(r: redis.Redis) -> int:
            n = int(r.incr(key))
            if n == 1:
                r.expire(key, 3600)
            return n

        return self._run(_incr)

    def clear_requeue_count(self, task_id: Union[str, int]) -> None:
        key = f"queue:requeue_count:{task_id}"
        self._run(lambda r: r.delete(key))

    def queue_depth_ready(self) -> int:
        return int(self._run(lambda r: r.llen(self.ready)))

    def queue_depth_scheduled(self) -> int:
        return int(self._run(lambda r: r.zcard(self.delayed)))

    def queue_depth_retry(self) -> int:
        return int(self._run(lambda r: r.zcard(self.retry)))

    def queue_depth_dead(self) -> int:
        return int(self._run(lambda r: r.llen(self.dead)))

    # legacy metric names
    def queue_depth_delayed(self) -> int:
        return self.queue_depth_scheduled()

    @staticmethod
    def _parse_id(raw: str) -> Optional[str]:
        raw = (raw or "").strip()
        if not raw:
            return None
        if raw.isdigit() or _UUID_RE.match(raw):
            return raw
        try:
            payload = json.loads(raw)
            if isinstance(payload, dict) and payload.get("id") is not None:
                return str(payload["id"])
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
        return None


def get_task_queue() -> TaskQueue:
    global _queue
    if _queue is None:
        _queue = TaskQueue(_get_redis())
    return _queue


TASKS_QUEUE_KEY = REDIS_QUEUE_TASKS


def _get_redis_queue_length() -> int:
    try:
        return get_task_queue().queue_depth_ready()
    except Exception:
        return 0
