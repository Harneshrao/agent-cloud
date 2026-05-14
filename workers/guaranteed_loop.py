"""
Production-oriented worker loop: dequeue → Redis lock → Postgres claim → visibility ZSET
→ idempotency gate → execute (optional circuit breaker) → result → task_events + metrics + JSON logs.

Run:
  WORKER_ID=worker-1 python -m workers.guaranteed_loop

Uses the same primitives as `workers.execution_worker` with observability hooks.
"""

from __future__ import annotations

import importlib
import logging
import os
import re
import threading
import time
import uuid

from database.db import db
from database.task_idempotency import delete_record, get_result, set_completed, try_claim
from redis_queue_pkg.locks import acquire_task_lock, release_task_lock
from redis_queue_pkg.redis_queue import TaskQueue, get_task_queue
from services.task_service import (
    claim_task_running,
    update_task_status,
    update_task_heartbeat,
)

from agent_cloud.core.resilience.circuit_breaker import CircuitBreaker, CircuitOpenError
from agent_cloud.infra.db.task_events_repo import emit_task_event
from agent_cloud.infra.observability.context import reset_trace_id, set_trace_id
from agent_cloud.infra.observability.metrics import Metrics
from agent_cloud.infra.observability.structured_log import JsonFormatter, get_logger

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.I,
)

_EXEC_BREAKER = CircuitBreaker(
    failure_threshold=int(os.environ.get("EXEC_CB_FAILURES", "5")),
    cooldown_sec=float(os.environ.get("EXEC_CB_COOLDOWN_SEC", "30")),
    name="executor",
)


def _configure_root_json_logging() -> logging.Logger:
    root = logging.getLogger()
    if not any(isinstance(h.formatter, JsonFormatter) for h in root.handlers):
        import sys

        h = logging.StreamHandler(sys.stdout)
        h.setFormatter(JsonFormatter())
        root.addHandler(h)
        root.setLevel(logging.INFO)
    return get_logger("workers.guaranteed_loop")


log = _configure_root_json_logging()


def _emit(task_uuid: uuid.UUID, event_type: str, payload: dict | None = None) -> None:
    try:
        emit_task_event(task_uuid, event_type, payload)
    except Exception:
        log.warning(
            "task_event_emit_failed",
            extra={"task_id": str(task_uuid), "event_type": event_type},
        )


def _visibility_ms() -> int:
    return int(float(os.environ.get("VISIBILITY_TIMEOUT_SEC", "300")) * 1000)


def _block_timeout() -> int:
    return int(os.environ.get("REDIS_QUEUE_BLOCK_TIMEOUT", "30"))


def _run_executor(task_dict: dict) -> object:
    mod = os.environ.get("EXECUTOR_MODULE", "").strip()
    fn = os.environ.get("EXECUTOR_CALLABLE", "run").strip()
    if mod:

        def _call() -> object:
            m = importlib.import_module(mod)
            return getattr(m, fn)(task_dict)

        return _EXEC_BREAKER.call(_call)
    return {"status": "noop", "task_id": str(task_dict.get("id"))}


def _resolve_idempotency_key(task: dict) -> str:
    k = task.get("idempotency_key")
    if k is not None and str(k).strip():
        return str(k).strip()
    wf = task.get("workflow_id")
    node = task.get("node_id")
    if wf is not None and node is not None:
        return f"{wf}:{node}"
    return str(task["id"])


_tasks_running = 0
_current_task_id: str | None = None
_tasks_lock = threading.Lock()


def _heartbeat_loop() -> None:
    while True:
        time.sleep(10)
        with _tasks_lock:
            tid = _current_task_id
        if tid is None:
            continue
        try:
            update_task_heartbeat(tid)
            Metrics.inc(Metrics.WORKER_HEARTBEAT)
        except Exception:
            pass


threading.Thread(target=_heartbeat_loop, daemon=True).start()


def loop_once() -> bool:
    """Return True if work was attempted (idle poll returns False)."""
    global _tasks_running, _current_task_id
    q = get_task_queue()
    raw = q.dequeue_blocking(_block_timeout())
    if not raw:
        return False
    tid = TaskQueue._parse_id(raw)
    if tid is None or not _UUID_RE.match(str(tid)):
        return True
    tid_str = str(tid)
    trace_tok = set_trace_id(tid_str)
    t0 = time.perf_counter()
    try:
        if not acquire_task_lock(
            tid_str, ttl_s=int(float(os.environ.get("LOCK_TTL_SEC", "300")))
        ):
            q.lpush_raw(raw)
            return True
        try:
            task = claim_task_running(tid_str)
            if task is None:
                q.lpush_raw(raw)
                return True
            task_uuid = uuid.UUID(tid_str)
            _emit(task_uuid, "worker_claimed", {"worker": os.environ.get("WORKER_ID")})
            Metrics.inc(Metrics.TASK_CLAIMED)

            idem_key = _resolve_idempotency_key(task)
            claimed, existing_status = try_claim(idem_key, task["id"])
            if not claimed:
                if existing_status == "completed":
                    stored = get_result(idem_key)
                    update_task_status(task["id"], "completed")
                    if stored is not None:
                        db.store_result(task["id"], stored)
                    _emit(task_uuid, "idempotent_skip", {"reason": "completed"})
                    return True
                _emit(
                    task_uuid,
                    "idempotent_skip",
                    {"reason": "concurrent_or_retry", "existing": existing_status},
                )
                return True

            deadline_ms = int(time.time() * 1000) + _visibility_ms()
            q.add_processing(tid_str, deadline_ms)
            with _tasks_lock:
                _tasks_running = 1
                _current_task_id = tid_str

            latency_ms = (time.perf_counter() - t0) * 1000
            Metrics.set_gauge(Metrics.QUEUE_LATENCY_MS, latency_ms)
            _emit(task_uuid, "execute_start", {})

            try:
                result = _run_executor(task)
                db.store_result(task_uuid, result)
                set_completed(idem_key, result)
                update_task_status(task_uuid, "completed")
                _emit(task_uuid, "execute_complete", {"ok": True})
                Metrics.inc(Metrics.TASK_COMPLETED)
            except CircuitOpenError as e:
                delete_record(idem_key)
                update_task_status(task_uuid, "failed")
                _emit(
                    task_uuid,
                    "execute_failed",
                    {"error": str(e), "kind": "circuit_open"},
                )
                Metrics.inc(Metrics.TASK_FAILED)
                log.warning(
                    "executor circuit open",
                    extra={"task_id": tid_str, "error": str(e)},
                )
            except Exception as e:
                delete_record(idem_key)
                update_task_status(task_uuid, "failed")
                _emit(
                    task_uuid,
                    "execute_failed",
                    {"error": str(e), "kind": "exception"},
                )
                Metrics.inc(Metrics.TASK_FAILED)
                log.exception(
                    "task execution failed",
                    extra={"task_id": tid_str},
                )
            finally:
                q.remove_processing(tid_str)
        finally:
            release_task_lock(tid_str)
            with _tasks_lock:
                _tasks_running = 0
                _current_task_id = None
    finally:
        reset_trace_id(trace_tok)
    return True


def main() -> None:
    log.info(
        "guaranteed_loop started",
        extra={"worker_id": os.environ.get("WORKER_ID")},
    )
    while True:
        try:
            if not loop_once():
                time.sleep(0.5)
        except Exception as e:
            log.exception("loop error", extra={"error": str(e)})
            time.sleep(1.0)


if __name__ == "__main__":
    main()
