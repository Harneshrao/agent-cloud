"""
Canonical operational logging — JSON stdout + durable task_logs rows.

Required fields (when known): timestamp, task_id, project_id, worker_id, deployment_id,
queue_name, execution_id, retry_count, runtime_version, severity, event_type.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from agent_cloud.infra.observability.operational_context import snapshot
from agent_cloud.infra.observability.structured_log import JsonFormatter, get_logger

_logger = get_logger("agent_cloud.operational")


def _persist_task_log(
    task_id: uuid.UUID,
    event_type: str,
    severity: str,
    payload: dict[str, Any],
) -> None:
    try:
        from database.task_observability import append_task_log_row

        append_task_log_row(task_id, event_type, severity, payload)
    except Exception:
        _logger.warning(
            "task_log_persist_failed",
            extra={"task_id": str(task_id), "event_type": event_type},
        )


def log_event(
    event_type: str,
    message: str,
    *,
    severity: str = "INFO",
    task_id: str | uuid.UUID | None = None,
    project_id: str | uuid.UUID | None = None,
    deployment_id: str | uuid.UUID | None = None,
    worker_id: str | None = None,
    queue_name: str | None = None,
    retry_count: int | None = None,
    runtime_version: str | None = None,
    persist: bool = True,
    **extra: Any,
) -> dict[str, Any]:
    """
    Emit one operational log record. Returns the payload written.
    """
    ctx = snapshot()
    record: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "severity": severity.upper(),
        "event_type": event_type,
        "message": message,
        "task_id": str(task_id) if task_id is not None else ctx.get("task_id"),
        "project_id": str(project_id) if project_id is not None else ctx.get("project_id"),
        "deployment_id": (
            str(deployment_id) if deployment_id is not None else ctx.get("deployment_id")
        ),
        "worker_id": worker_id or ctx.get("worker_id"),
        "queue_name": queue_name or ctx.get("queue_name"),
        "execution_id": ctx.get("execution_id"),
        "retry_count": retry_count if retry_count is not None else ctx.get("retry_count"),
        "runtime_version": runtime_version or ctx.get("runtime_version"),
        "trace_id": ctx.get("trace_id"),
    }
    record.update(extra)

    level = logging.INFO
    if severity.upper() in ("ERROR", "CRITICAL"):
        level = logging.ERROR
    elif severity.upper() == "WARNING":
        level = logging.WARNING
    _logger.log(level, message, extra=record)

    tid = record.get("task_id")
    if persist and tid:
        try:
            _persist_task_log(uuid.UUID(str(tid)), event_type, severity.upper(), record)
        except (ValueError, TypeError):
            pass

    return record


def emit_task_trace_event(
    task_id: uuid.UUID,
    event_type: str,
    payload: Optional[dict] = None,
    *,
    severity: str = "INFO",
) -> None:
    """Append to task_events (canonical trace) + task_logs + JSON stdout."""
    merged = {**snapshot(), **(payload or {})}
    merged["event_type"] = event_type
    merged["severity"] = severity
    try:
        from agent_cloud.infra.db.task_events_repo import emit_task_event

        emit_task_event(task_id, event_type, merged)
    except Exception:
        _logger.warning(
            "task_event_emit_failed",
            extra={"task_id": str(task_id), "event_type": event_type},
        )
    _logger.info(event_type, extra=merged)
    try:
        from database.task_observability import append_task_log_row

        append_task_log_row(task_id, event_type, severity.upper(), merged)
    except Exception:
        pass
