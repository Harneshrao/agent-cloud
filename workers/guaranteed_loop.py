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
from services.task_payload import parse_payload
from services.task_service import (
    claim_task_running,
    update_task_status,
    update_task_heartbeat,
)
from workers.agent_executor import ExecutionSecurityError
from workers.dequeue_filters import task_matches_worker
from workers.task_outcome import handle_failure

from agent_cloud.core.resilience.circuit_breaker import CircuitBreaker, CircuitOpenError
from agent_cloud.infra.observability.metrics import Metrics
from agent_cloud.infra.observability.operational_context import bind_execution, clear_execution
from agent_cloud.infra.observability.operational_log import emit_task_trace_event
from agent_cloud.infra.observability.structured_log import JsonFormatter, get_logger
from config.redis_keys import REDIS_QUEUE_READY

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


def _trace(
    task_uuid: uuid.UUID,
    event_type: str,
    payload: dict | None = None,
    *,
    severity: str = "INFO",
) -> None:
    emit_task_trace_event(task_uuid, event_type, payload, severity=severity)


def _record_failure_metering(
    task: dict, task_uuid: uuid.UUID, error: str
) -> None:
    pid = db.get_task_project_id(task_uuid)
    if pid is None:
        return
    try:
        from services.usage_metering import record_task_failed

        dep = task.get("deployment_id")
        record_task_failed(
            pid,
            task_uuid,
            error=error,
            deployment_id=uuid.UUID(str(dep)) if dep else None,
        )
    except Exception:
        pass


def _visibility_ms() -> int:
    return int(float(os.environ.get("VISIBILITY_TIMEOUT_SEC", "300")) * 1000)


def _block_timeout() -> int:
    return int(os.environ.get("REDIS_QUEUE_BLOCK_TIMEOUT", "30"))


def _run_executor(task_dict: dict) -> object:
    mod = os.environ.get("EXECUTOR_MODULE", "workers.agent_executor").strip()
    fn = os.environ.get("EXECUTOR_CALLABLE", "run").strip()

    def _call() -> object:
        m = importlib.import_module(mod)
        return getattr(m, fn)(task_dict)

    return _EXEC_BREAKER.call(_call)


def _worker_filter_env() -> tuple[list[str] | None, str | None, str | None]:
    caps_raw = os.environ.get("WORKER_CAPABILITIES", "").strip()
    caps = [c.strip() for c in caps_raw.split(",") if c.strip()] if caps_raw else None
    region = os.environ.get("WORKER_REGION", "").strip() or None
    wtype = (os.environ.get("WORKER_TYPE", "").strip() or "").lower() or None
    return caps, region, wtype


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
    task_uuid = uuid.UUID(tid_str)
    row = db.fetch_task_by_id(tid_str)
    if row is None:
        return True
    parsed = parse_payload(row.get("task_text"))
    project_id = row.get("project_id")
    trace_tok = bind_execution(
        task_id=tid_str,
        project_id=str(project_id) if project_id else None,
        deployment_id=parsed.get("deployment_id"),
        queue_name=REDIS_QUEUE_READY,
        runtime_version=parsed.get("runtime"),
        retry_count=None,
    )
    _trace(task_uuid, "dequeued", {"queue_name": REDIS_QUEUE_READY})
    caps, region, wtype = _worker_filter_env()
    if not task_matches_worker(
        parsed,
        worker_capabilities=caps,
        worker_region=region,
        worker_type=wtype,
    ):
        q.lpush_raw(raw)
        return True

    t0 = time.perf_counter()
    try:
        if not acquire_task_lock(
            tid_str, ttl_s=int(float(os.environ.get("LOCK_TTL_SEC", "300")))
        ):
            _trace(task_uuid, "lock_denied", {})
            q.lpush_raw(raw)
            return True
        try:
            task = claim_task_running(tid_str)
            if task is None:
                _trace(task_uuid, "claim_skipped", {})
                q.lpush_raw(raw)
                return True
            _trace(task_uuid, "claimed", {"worker_id": os.environ.get("WORKER_ID")})
            Metrics.inc(Metrics.TASK_CLAIMED)

            idem_key = _resolve_idempotency_key(task)
            claimed, existing_status = try_claim(idem_key, task["id"])
            if not claimed:
                if existing_status == "completed":
                    stored = get_result(idem_key)
                    update_task_status(task["id"], "completed")
                    if stored is not None:
                        db.store_result(task["id"], stored)
                    _trace(task_uuid, "idempotent_skip", {"reason": "completed"})
                    return True
                _trace(
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
            _trace(task_uuid, "execute_start", {})

            try:
                result = _run_executor(task)
                exec_ms = int((time.perf_counter() - t0) * 1000)
                db.store_result(task_uuid, result)
                set_completed(idem_key, result)
                update_task_status(task_uuid, "completed")
                _trace(task_uuid, "execute_complete", {"ok": True, "execution_ms": exec_ms})
                Metrics.inc(Metrics.TASK_COMPLETED)
                pid = db.get_task_project_id(task_uuid)
                if pid is not None:
                    try:
                        from services.usage_metering import record_task_completed

                        dep = task.get("deployment_id")
                        record_task_completed(
                            pid,
                            task_uuid,
                            execution_time_ms=exec_ms,
                            agent_name=str(task.get("agent") or ""),
                            deployment_id=uuid.UUID(str(dep)) if dep else None,
                        )
                        from services.product_analytics import track_first_task_completed

                        track_first_task_completed(
                            pid,
                            task_uuid,
                            deployment_id=uuid.UUID(str(dep)) if dep else None,
                        )
                    except Exception:
                        pass
            except CircuitOpenError as e:
                _record_failure_metering(task, task_uuid, str(e))
                outcome = handle_failure(
                    task,
                    e,
                    idem_key,
                    emit=lambda tid, ev, pl: _trace(tid, ev, pl),
                )
                _trace(
                    task_uuid,
                    "execute_failed",
                    {"error": str(e), "kind": "circuit_open", "outcome": outcome},
                    severity="ERROR",
                )
                Metrics.inc(Metrics.TASK_FAILED)
                log.warning(
                    "executor circuit open",
                    extra={"task_id": tid_str, "error": str(e), "outcome": outcome},
                )
            except ExecutionSecurityError as e:
                _record_failure_metering(task, task_uuid, str(e))
                outcome = handle_failure(
                    task,
                    e,
                    idem_key,
                    emit=lambda tid, ev, pl: _trace(tid, ev, pl),
                )
                _trace(
                    task_uuid,
                    "execute_failed",
                    {"error": str(e), "kind": "security", "outcome": outcome},
                    severity="ERROR",
                )
                Metrics.inc(Metrics.TASK_FAILED)
                log.warning(
                    "task security limit",
                    extra={"task_id": tid_str, "error": str(e), "outcome": outcome},
                )
            except Exception as e:
                outcome = handle_failure(
                    task,
                    e,
                    idem_key,
                    emit=lambda tid, ev, pl: _trace(tid, ev, pl),
                )
                _trace(
                    task_uuid,
                    "execute_failed",
                    {"error": str(e), "kind": "exception", "outcome": outcome},
                    severity="ERROR",
                )
                Metrics.inc(Metrics.TASK_FAILED)
                log.exception(
                    "task execution failed",
                    extra={"task_id": tid_str, "outcome": outcome},
                )
            finally:
                q.remove_processing(tid_str)
        finally:
            release_task_lock(tid_str)
            with _tasks_lock:
                _tasks_running = 0
                _current_task_id = None
    finally:
        clear_execution(trace_tok)
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
