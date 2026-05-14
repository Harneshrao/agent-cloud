"""
Reference stateless worker: BRPOP → lock → claim (Postgres) → visibility ZSET → execute → complete.

Uses `services.task_service.claim_task_running` after dequeue (same contract as `workers/worker.py`).

Run:
  WORKER_ID=worker-1 python -m workers.execution_worker
"""

from __future__ import annotations

import importlib
import os
import re
import time
import uuid

from database.db import db
from redis_queue_pkg.locks import acquire_task_lock, release_task_lock
from redis_queue_pkg.redis_queue import TaskQueue, get_task_queue
from services.task_service import claim_task_running, update_task_status

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I
)


def _visibility_ms() -> int:
    return int(float(os.environ.get("VISIBILITY_TIMEOUT_SEC", "300")) * 1000)


def _block_timeout() -> int:
    return int(os.environ.get("REDIS_QUEUE_BLOCK_TIMEOUT", "30"))


def _run_executor(task_dict: dict) -> object:
    mod = os.environ.get("EXECUTOR_MODULE", "").strip()
    fn = os.environ.get("EXECUTOR_CALLABLE", "run").strip()
    if mod:
        m = importlib.import_module(mod)
        return getattr(m, fn)(task_dict)
    return {"status": "noop", "task_id": str(task_dict.get("id"))}


def loop_once() -> bool:
    """Return True if a task was processed or skipped (caller should continue)."""
    q = get_task_queue()
    raw = q.dequeue_blocking(_block_timeout())
    if not raw:
        return False
    tid = TaskQueue._parse_id(raw)
    if tid is None or not _UUID_RE.match(str(tid)):
        return True
    if not acquire_task_lock(tid, ttl_s=int(float(os.environ.get("LOCK_TTL_SEC", "300")))):
        q.lpush_raw(raw)
        return True
    try:
        task = claim_task_running(str(tid))
        if task is None:
            q.lpush_raw(raw)
            return True
        deadline_ms = int(time.time() * 1000) + _visibility_ms()
        q.add_processing(tid, deadline_ms)
        task_uuid = uuid.UUID(str(tid))
        try:
            result = _run_executor(task)
            db.store_result(task_uuid, result)
        except Exception:
            update_task_status(task_uuid, "failed")
            raise
        finally:
            q.remove_processing(tid)
    finally:
        release_task_lock(tid)
    return True


def main() -> None:
    print("execution_worker started; WORKER_ID=", os.environ.get("WORKER_ID"))
    while True:
        try:
            if not loop_once():
                time.sleep(0.5)
        except Exception as e:
            print("task error:", e)
            time.sleep(1.0)


if __name__ == "__main__":
    main()
