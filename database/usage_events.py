"""
Canonical usage ledger — append-only events for billing and quotas.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, func, select

from database.models import Task, TaskStatus, UsageEvent
from database.session import SessionLocal

# Event types (billable / metered)
EVENT_TASK_ENQUEUED = "task_enqueued"
EVENT_TASK_COMPLETED = "task_completed"
EVENT_TASK_FAILED = "task_failed"
EVENT_TASK_RETRY = "task_retry"
EVENT_TASK_DLQ = "task_dlq"
EVENT_DEPLOYMENT_CREATED = "deployment_created"
EVENT_ARTIFACT_UPLOADED = "artifact_uploaded"
EVENT_API_REQUEST = "api_request"
EVENT_EXECUTION_MS = "execution_ms"


def record_usage_event(
    project_id: uuid.UUID,
    event_type: str,
    *,
    quantity: float = 1.0,
    unit: str = "count",
    task_id: Optional[uuid.UUID] = None,
    deployment_id: Optional[uuid.UUID] = None,
    artifact_id: Optional[uuid.UUID] = None,
    api_key_id: Optional[int] = None,
    metadata: Optional[dict] = None,
) -> uuid.UUID:
    with SessionLocal() as session:
        row = UsageEvent(
            project_id=project_id,
            event_type=event_type,
            quantity=quantity,
            unit=unit,
            task_id=task_id,
            deployment_id=deployment_id,
            artifact_id=artifact_id,
            api_key_id=api_key_id,
            event_metadata=metadata or {},
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return row.id


def count_events(
    project_id: uuid.UUID,
    event_type: str,
    *,
    since: Optional[datetime] = None,
) -> float:
    with SessionLocal() as session:
        q = select(func.coalesce(func.sum(UsageEvent.quantity), 0)).where(
            UsageEvent.project_id == project_id,
            UsageEvent.event_type == event_type,
        )
        if since is not None:
            q = q.where(UsageEvent.created_at >= since)
        return float(session.scalar(q) or 0)


def sum_quantity_by_unit(
    project_id: uuid.UUID,
    event_type: str,
    unit: str,
    *,
    since: Optional[datetime] = None,
) -> float:
    with SessionLocal() as session:
        q = select(func.coalesce(func.sum(UsageEvent.quantity), 0)).where(
            UsageEvent.project_id == project_id,
            UsageEvent.event_type == event_type,
            UsageEvent.unit == unit,
        )
        if since is not None:
            q = q.where(UsageEvent.created_at >= since)
        return float(session.scalar(q) or 0)


def count_running_tasks(project_id: uuid.UUID) -> int:
    with SessionLocal() as session:
        n = session.scalar(
            select(func.count())
            .select_from(Task)
            .where(
                Task.project_id == project_id,
                Task.status == TaskStatus.running,
            )
        )
        return int(n or 0)


def list_usage_events(
    project_id: uuid.UUID,
    *,
    limit: int = 100,
    event_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    with SessionLocal() as session:
        q = select(UsageEvent).where(UsageEvent.project_id == project_id)
        if event_type:
            q = q.where(UsageEvent.event_type == event_type)
        q = q.order_by(desc(UsageEvent.created_at)).limit(limit)
        rows = session.scalars(q).all()
        return [
            {
                "event_id": str(r.id),
                "project_id": str(r.project_id),
                "event_type": r.event_type,
                "quantity": r.quantity,
                "unit": r.unit,
                "task_id": str(r.task_id) if r.task_id else None,
                "deployment_id": str(r.deployment_id) if r.deployment_id else None,
                "metadata": r.event_metadata or {},
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]


def usage_breakdown_month(project_id: uuid.UUID) -> Dict[str, Any]:
    """Aggregate current UTC month by event_type."""
    month_start = datetime.now(timezone.utc).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    with SessionLocal() as session:
        rows = session.execute(
            select(
                UsageEvent.event_type,
                UsageEvent.unit,
                func.sum(UsageEvent.quantity).label("total"),
            )
            .where(
                UsageEvent.project_id == project_id,
                UsageEvent.created_at >= month_start,
            )
            .group_by(UsageEvent.event_type, UsageEvent.unit)
        ).all()
    by_type: Dict[str, float] = {}
    execution_ms = 0.0
    for event_type, unit, total in rows:
        key = f"{event_type}:{unit}"
        by_type[key] = float(total or 0)
        if event_type == EVENT_EXECUTION_MS or unit == "ms":
            execution_ms += float(total or 0)
        if event_type == EVENT_TASK_COMPLETED:
            by_type["task_completed"] = by_type.get("task_completed", 0) + float(total or 0)
    return {
        "period_start": month_start.isoformat(),
        "by_type": by_type,
        "tasks_enqueued": count_events(project_id, EVENT_TASK_ENQUEUED, since=month_start),
        "tasks_completed": count_events(project_id, EVENT_TASK_COMPLETED, since=month_start),
        "tasks_failed": count_events(project_id, EVENT_TASK_FAILED, since=month_start),
        "retries": count_events(project_id, EVENT_TASK_RETRY, since=month_start),
        "dlq_entries": count_events(project_id, EVENT_TASK_DLQ, since=month_start),
        "execution_time_ms": int(
            sum_quantity_by_unit(project_id, EVENT_EXECUTION_MS, "ms", since=month_start)
            or execution_ms
        ),
        "deployments": count_events(project_id, EVENT_DEPLOYMENT_CREATED, since=month_start),
        "artifact_uploads": count_events(project_id, EVENT_ARTIFACT_UPLOADED, since=month_start),
    }


def retries_last_hour(project_id: uuid.UUID) -> float:
    since = datetime.now(timezone.utc) - timedelta(hours=1)
    return count_events(project_id, EVENT_TASK_RETRY, since=since)
