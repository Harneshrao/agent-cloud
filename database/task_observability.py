"""
Task traces, logs, queue snapshots, and project-scoped DLQ queries.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, func, select

from config.redis_keys import REDIS_QUEUE_PROCESSING, REDIS_QUEUE_READY, REDIS_QUEUE_RETRY
from database.dead_letter import list_dead_letters
from database.models import AgentRun, Task, TaskEvent, TaskLog, TaskStatus
from database.session import SessionLocal
from redis_queue_pkg.redis_queue import get_task_queue


def append_task_log_row(
    task_id: uuid.UUID,
    event_type: str,
    severity: str,
    payload: dict[str, Any],
) -> uuid.UUID:
    message = json.dumps(
        {
            "event_type": event_type,
            "severity": severity,
            **payload,
        },
        default=str,
    )
    with SessionLocal() as session:
        row = TaskLog(task_id=task_id, message=message)
        session.add(row)
        session.commit()
        session.refresh(row)
        return row.id


def list_task_events(task_id: uuid.UUID, limit: int = 200) -> List[Dict[str, Any]]:
    with SessionLocal() as session:
        rows = session.scalars(
            select(TaskEvent)
            .where(TaskEvent.task_id == task_id)
            .order_by(TaskEvent.created_at.asc())
            .limit(limit)
        ).all()
        return [
            {
                "event_id": str(e.id),
                "task_id": str(e.task_id),
                "event_type": e.event_type,
                "payload": e.payload or {},
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in rows
        ]


def list_task_logs(task_id: uuid.UUID, limit: int = 500) -> List[Dict[str, Any]]:
    with SessionLocal() as session:
        rows = session.scalars(
            select(TaskLog)
            .where(TaskLog.task_id == task_id)
            .order_by(TaskLog.created_at.asc())
            .limit(limit)
        ).all()
        out: List[Dict[str, Any]] = []
        for row in rows:
            try:
                body = json.loads(row.message)
            except (json.JSONDecodeError, TypeError):
                body = {"message": row.message}
            body["log_id"] = str(row.id)
            body["created_at"] = (
                row.created_at.isoformat() if row.created_at else None
            )
            out.append(body)
        return out


def get_task_detail(task_id: uuid.UUID) -> Optional[Dict[str, Any]]:
    with SessionLocal() as session:
        t = session.get(Task, task_id)
        if t is None:
            return None
        return {
            "task_id": str(t.id),
            "project_id": str(t.project_id),
            "status": t.status.value if hasattr(t.status, "value") else str(t.status),
            "retry_count": t.retry_count,
            "max_retries": t.max_retries,
            "worker_id": t.worker_id,
            "input": t.input_json or {},
            "output": t.output_json,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "started_at": t.started_at.isoformat() if t.started_at else None,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            "idempotency_key": t.idempotency_key,
        }


def build_task_trace(task_id: uuid.UUID) -> Dict[str, Any]:
    """Unified lifecycle view: task row + ordered events + logs."""
    detail = get_task_detail(task_id)
    if detail is None:
        return {}
    events = list_task_events(task_id)
    logs = list_task_logs(task_id)
    phases = [
        "enqueued",
        "dequeued",
        "lock_denied",
        "claimed",
        "claim_skipped",
        "execute_start",
        "execute_complete",
        "execute_failed",
        "retry_scheduled",
        "dlq",
        "idempotent_skip",
    ]
    seen = {e["event_type"] for e in events}
    return {
        "task": detail,
        "events": events,
        "logs": logs,
        "lifecycle_complete": all(
            t in seen for t in ("enqueued", "claimed", "execute_complete")
        )
        or "dlq" in seen
        or detail.get("status") in ("completed", "failed", "dead"),
        "expected_phases": phases,
    }


def list_tasks_for_project(
    project_id: uuid.UUID, limit: int = 50, status: Optional[str] = None
) -> List[Dict[str, Any]]:
    with SessionLocal() as session:
        q = select(Task).where(Task.project_id == project_id)
        if status:
            try:
                q = q.where(Task.status == TaskStatus(status))
            except ValueError:
                pass
        q = q.order_by(desc(Task.created_at)).limit(limit)
        rows = session.scalars(q).all()
        return [
            {
                "task_id": str(t.id),
                "status": t.status.value if hasattr(t.status, "value") else str(t.status),
                "retry_count": t.retry_count,
                "worker_id": t.worker_id,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "agent": (t.input_json or {}).get("agent"),
                "deployment_id": (t.input_json or {}).get("deployment_id"),
            }
            for t in rows
        ]


def queue_snapshot() -> Dict[str, Any]:
    """Redis queue depths + processing/retry visibility."""
    q = get_task_queue()
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    try:
        processing_due = int(q.r.zcount(q.processing, "-inf", now_ms) or 0)
    except Exception:
        processing_due = 0

    return {
        "queue_ready": q.queue_depth_ready(),
        "queue_retry": q.queue_depth_retry(),
        "queue_scheduled": q.queue_depth_scheduled(),
        "queue_dead_redis": q.queue_depth_dead(),
        "visibility_stale_count": processing_due,
        "keys": {
            "ready": REDIS_QUEUE_READY,
            "retry": REDIS_QUEUE_RETRY,
            "processing": REDIS_QUEUE_PROCESSING,
        },
    }


def list_dlq_for_project(project_id: uuid.UUID, limit: int = 100) -> List[Dict[str, Any]]:
    """DLQ entries whose task_id belongs to this project."""
    all_dlq = list_dead_letters(limit=500)
    if not all_dlq:
        return []
    out: List[Dict[str, Any]] = []
    with SessionLocal() as session:
        for item in all_dlq:
            tid_raw = item.get("task_id")
            if not tid_raw:
                continue
            try:
                tid = uuid.UUID(str(tid_raw))
            except ValueError:
                continue
            t = session.get(Task, tid)
            if t is None or t.project_id != project_id:
                continue
            out.append({**item, "project_id": str(project_id)})
            if len(out) >= limit:
                break
    return out


def task_counts_for_project(project_id: uuid.UUID, hours: int = 24) -> Dict[str, Any]:
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    with SessionLocal() as session:
        rows = session.execute(
            select(Task.status, func.count())
            .where(Task.project_id == project_id, Task.created_at >= since)
            .group_by(Task.status)
        ).all()
        by_status = {
            (s.value if hasattr(s, "value") else str(s)): int(c) for s, c in rows
        }
        failed = by_status.get("failed", 0) + by_status.get("dead", 0)
        completed = by_status.get("completed", 0)
        total = sum(by_status.values())
        return {
            "hours": hours,
            "by_status": by_status,
            "total": total,
            "failed": failed,
            "completed": completed,
            "failure_rate": round(failed / total, 4) if total else 0.0,
        }


def list_agent_runs_for_task(task_id: uuid.UUID) -> List[Dict[str, Any]]:
    with SessionLocal() as session:
        rows = session.scalars(
            select(AgentRun)
            .where(AgentRun.task_id == task_id)
            .order_by(AgentRun.id.asc())
        ).all()
        return [
            {
                "run_id": str(r.id),
                "agent_name": r.agent_name,
                "status": r.status.value if hasattr(r.status, "value") else str(r.status),
                "output": r.output,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            }
            for r in rows
        ]
