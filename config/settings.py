"""Application settings (env-driven)."""

from __future__ import annotations

import os
from pathlib import Path

# Load repo-root .env before reading DATABASE_URL (does not override existing env vars).
try:
    from dotenv import load_dotenv

    _REPO_ROOT = Path(__file__).resolve().parents[1]
    load_dotenv(_REPO_ROOT / ".env")
except ImportError:
    pass

_raw_db = os.environ.get("DATABASE_URL", "").strip()
if not _raw_db:
    raise RuntimeError(
        "DATABASE_URL is not set. Copy .env.example to .env and set DATABASE_URL, "
        "or export DATABASE_URL in the environment (Docker/Kubernetes set this explicitly)."
    )
DATABASE_URL = _raw_db

# Seeded by Alembic migration — used when project_id is omitted (enqueue_task)
DEFAULT_USER_UUID = os.environ.get(
    "DEFAULT_USER_UUID", "00000000-0000-4000-8000-000000000001"
)
DEFAULT_PROJECT_UUID = os.environ.get(
    "DEFAULT_PROJECT_UUID", "00000000-0000-4000-8000-000000000002"
)

# Redis — queue, scheduling, locks
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# Comma-separated list, e.g. https://app.example.com,https://staging.example.com
# Empty → API defaults to http://localhost:3000 for local dev only (set explicit origins in prod).
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "").strip()

# Canonical keys (see config/redis_keys.py). Namespace prefix optional for multi-tenant Redis.
from config.redis_keys import (  # noqa: E402
    REDIS_QUEUE_DEAD,
    REDIS_QUEUE_RETRY,
    REDIS_QUEUE_SCHEDULED,
    REDIS_QUEUE_TASKS,
    idempotency_key,
    lock_task_key,
)

# Back-compat aliases for metrics / older imports
REDIS_QUEUE_READY = REDIS_QUEUE_TASKS
REDIS_QUEUE_DELAYED = REDIS_QUEUE_SCHEDULED
REDIS_QUEUE_PREFIX = "queue"  # informational; keys are fixed in redis_keys
REDIS_LOCK_PREFIX = "lock:task"  # use lock_task_key() for full key

DEFAULT_BLOCK_TIMEOUT = int(os.environ.get("REDIS_QUEUE_BLOCK_TIMEOUT", "30"))

# Retry backoff (ms base for 2**retry_count * base)
RETRY_BACKOFF_BASE_MS = int(os.environ.get("RETRY_BACKOFF_BASE_MS", "1000"))
MAX_TASK_RETRIES = int(os.environ.get("MAX_TASK_RETRIES", "5"))
