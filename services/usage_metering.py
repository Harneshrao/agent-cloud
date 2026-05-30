"""
Record canonical usage events — call from enqueue, worker, deployments, API edge.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from database import usage_events as usage_db
from database.usage_records import record_usage as record_legacy_usage


def record_task_enqueued(
    project_id: uuid.UUID,
    task_id: uuid.UUID,
    *,
    deployment_id: Optional[uuid.UUID] = None,
    agent_name: Optional[str] = None,
    api_key_id: Optional[int] = None,
) -> None:
    usage_db.record_usage_event(
        project_id,
        usage_db.EVENT_TASK_ENQUEUED,
        task_id=task_id,
        deployment_id=deployment_id,
        metadata={"agent": agent_name},
        api_key_id=api_key_id,
    )


def record_task_completed(
    project_id: uuid.UUID,
    task_id: uuid.UUID,
    *,
    execution_time_ms: int,
    agent_name: str = "",
    deployment_id: Optional[uuid.UUID] = None,
) -> None:
    usage_db.record_usage_event(
        project_id,
        usage_db.EVENT_TASK_COMPLETED,
        task_id=task_id,
        deployment_id=deployment_id,
        metadata={"agent": agent_name},
    )
    if execution_time_ms > 0:
        usage_db.record_usage_event(
            project_id,
            usage_db.EVENT_EXECUTION_MS,
            quantity=float(execution_time_ms),
            unit="ms",
            task_id=task_id,
        )
    try:
        record_legacy_usage(
            project_id=project_id,
            task_id=task_id,
            agent_name=agent_name or "agent",
            execution_time_ms=execution_time_ms,
            tokens_used=0,
            agent_cost=0.0,
        )
    except Exception:
        pass


def record_task_failed(
    project_id: uuid.UUID,
    task_id: uuid.UUID,
    *,
    error: str = "",
    deployment_id: Optional[uuid.UUID] = None,
) -> None:
    usage_db.record_usage_event(
        project_id,
        usage_db.EVENT_TASK_FAILED,
        task_id=task_id,
        deployment_id=deployment_id,
        metadata={"error": error[:500]},
    )


def record_task_retry(
    project_id: uuid.UUID,
    task_id: uuid.UUID,
    *,
    retry_count: int = 0,
) -> None:
    usage_db.record_usage_event(
        project_id,
        usage_db.EVENT_TASK_RETRY,
        task_id=task_id,
        metadata={"retry_count": retry_count},
    )


def record_task_dlq(
    project_id: uuid.UUID,
    task_id: uuid.UUID,
    *,
    error: str = "",
) -> None:
    usage_db.record_usage_event(
        project_id,
        usage_db.EVENT_TASK_DLQ,
        task_id=task_id,
        metadata={"error": error[:500]},
    )


def record_deployment_created(
    project_id: uuid.UUID,
    deployment_id: uuid.UUID,
    *,
    artifact_id: Optional[uuid.UUID] = None,
) -> None:
    usage_db.record_usage_event(
        project_id,
        usage_db.EVENT_DEPLOYMENT_CREATED,
        deployment_id=deployment_id,
        artifact_id=artifact_id,
    )


def record_artifact_uploaded(
    project_id: uuid.UUID,
    artifact_id: uuid.UUID,
    *,
    bytes_size: int,
    agent_name: str = "",
) -> None:
    usage_db.record_usage_event(
        project_id,
        usage_db.EVENT_ARTIFACT_UPLOADED,
        quantity=float(bytes_size),
        unit="bytes",
        artifact_id=artifact_id,
        metadata={"agent": agent_name},
    )


def record_api_request(project_id: uuid.UUID, *, path: str = "") -> None:
    usage_db.record_usage_event(
        project_id,
        usage_db.EVENT_API_REQUEST,
        metadata={"path": path[:200]},
    )
