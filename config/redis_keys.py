"""
Canonical Redis key layout (single control plane).

Override via env only if you namespace per environment (e.g. staging:queue:tasks).
"""

from __future__ import annotations

import os

_NS = os.environ.get("REDIS_KEY_NAMESPACE", "").strip()

def _k(name: str) -> str:
    return f"{_NS}{name}" if _NS else name


# Main runnable queue (BRPOP / LPUSH task_id as string UUID) — canonical name: queue:ready
REDIS_QUEUE_READY = _k("queue:ready")
REDIS_QUEUE_TASKS = REDIS_QUEUE_READY  # backward-compatible alias

# Visibility timeout / in-flight tracking (score = deadline epoch ms)
REDIS_QUEUE_PROCESSING = _k("queue:processing")

# Time-ordered work (score = unix milliseconds)
REDIS_QUEUE_SCHEDULED = _k("queue:scheduled")
REDIS_QUEUE_RETRY = _k("queue:retry")

# Terminal failures (optional JSON payloads)
REDIS_QUEUE_DEAD = _k("queue:dead")

# Per-task execution lock (SET key value NX EX ttl)
def lock_task_key(task_id: str) -> str:
    return _k(f"lock:task:{task_id}")


# Idempotency marker (SET NX EX or string value)
def idempotency_key(task_id: str) -> str:
    return _k(f"idempotency:{task_id}")


def rate_limit_user_key(user_id: str) -> str:
    """API / worker rate bucket (spec: rate:{user_id})."""
    return _k(f"rate:{user_id}")
