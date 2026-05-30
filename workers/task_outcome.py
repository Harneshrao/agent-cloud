"""
Retry, DLQ, and Postgres/Redis coordination for the canonical worker loop.

Aligns with docs/EXECUTION_PLATFORM.md: failed attempts → queue:retry (ZSET) with backoff;
exhausted retries → dead_letter_tasks + terminal status.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Callable, Dict, Optional

from database.db import db
from database.dead_letter import (
    MAX_RETRIES,
    increment_retry_count,
    insert_dead_letter,
)
from database.task_idempotency import delete_record
from execution.backoff import retry_deadline_ms
from redis_queue_pkg.redis_queue import get_task_queue
from services.task_service import update_task_status

EmitFn = Callable[[uuid.UUID, str, Optional[dict]], None]


def task_payload_json(task: Dict[str, Any]) -> str:
    payload = {
        "task": task.get("task", ""),
        "agent": task.get("agent"),
        "runtime": task.get("runtime"),
        "workflow_id": task.get("workflow_id"),
        "node_id": task.get("node_id"),
        "deps": task.get("deps"),
        "required_capabilities": task.get("required_capabilities"),
        "priority": task.get("priority"),
        "idempotency_key": task.get("idempotency_key"),
        "target_region": task.get("target_region"),
        "agent_instance_id": task.get("agent_instance_id"),
        "installation_id": task.get("installation_id"),
        "input": task.get("input"),
    }
    return json.dumps({k: v for k, v in payload.items() if v is not None})


def handle_failure(
    task: Dict[str, Any],
    error: Exception,
    idempotency_key: str,
    *,
    emit: Optional[EmitFn] = None,
) -> str:
    """
    Record failure outcome. Returns ``dlq`` or ``retry``.
    Clears idempotency lease so another attempt may run after backoff.
    """
    delete_record(idempotency_key)
    task_id = uuid.UUID(str(task["id"]))
    retry_count = increment_retry_count(task_id)
    err_text = str(error)
    task_payload = task_payload_json(task)

    def _emit(event: str, payload: Optional[dict] = None) -> None:
        if emit is not None:
            emit(task_id, event, payload)

    project_id = db.get_task_project_id(task_id)
    if project_id is not None:
        try:
            from services.usage_metering import record_task_dlq, record_task_retry
            from services.quota_service import check_retry_allowed

            if retry_count >= MAX_RETRIES:
                record_task_dlq(project_id, task_id, error=err_text)
            else:
                try:
                    check_retry_allowed(project_id)
                except Exception:
                    pass
                record_task_retry(project_id, task_id, retry_count=retry_count)
        except Exception:
            pass

    if retry_count >= MAX_RETRIES:
        insert_dead_letter(
            task_id=task_id,
            task_payload=task_payload,
            error=err_text,
            retry_count=retry_count,
            workflow_id=task.get("workflow_id"),
            node_id=task.get("node_id"),
            agent_name=task.get("agent"),
        )
        _notify_workflow_failed(task, task_id, error)
        update_task_status(task_id, "failed")
        try:
            get_task_queue().to_dead_letter(task_id, err_text)
        except Exception:
            pass
        _emit(
            "dlq",
            {
                "error": err_text,
                "retry_count": retry_count,
                "max_retries": MAX_RETRIES,
            },
        )
        return "dlq"

    if project_id is not None:
        try:
            from engine.quota_checker import QuotaExceeded
            from services.quota_service import check_retry_allowed

            check_retry_allowed(project_id)
        except Exception as qe:
            from engine.quota_checker import QuotaExceeded

            if isinstance(qe, QuotaExceeded):
                insert_dead_letter(
                    task_id=task_id,
                    task_payload=task_payload,
                    error=f"{err_text}; {qe}",
                    retry_count=retry_count,
                    workflow_id=task.get("workflow_id"),
                    node_id=task.get("node_id"),
                    agent_name=task.get("agent"),
                )
                update_task_status(task_id, "failed")
                _emit("dlq", {"error": str(qe), "reason": "retry_storm"})
                return "dlq"

    update_task_status(task_id, "retry")
    run_at_ms = retry_deadline_ms(retry_count - 1)
    get_task_queue().schedule_retry(task_id, run_at_ms)
    _emit(
        "retry_scheduled",
        {
            "error": err_text,
            "retry_count": retry_count,
            "max_retries": MAX_RETRIES,
            "run_at_ms": run_at_ms,
        },
    )
    return "retry"


def _notify_workflow_failed(
    task: Dict[str, Any], task_id: uuid.UUID, error: Exception
) -> None:
    if task.get("workflow_id") is None or task.get("node_id") is None:
        return
    try:
        from engine.dag_scheduler import on_node_failed

        on_node_failed(
            uuid.UUID(str(task["workflow_id"])),
            task["node_id"],
            task_id,
            error,
        )
    except Exception:
        pass
