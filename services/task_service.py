"""
Single pipeline: insert task metadata in Postgres, enqueue task_id on Redis LIST.
Workers: BRPOP → claim in Postgres → execute.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Union

from database.db import db
from redis_queue_pkg.redis_queue import TaskQueue, get_task_queue
from services.task_payload import ensure_task_capabilities, parse_payload, serialize_payload


def _task_id_str(task_id: Union[int, str, uuid.UUID]) -> str:
    if isinstance(task_id, uuid.UUID):
        return str(task_id)
    s = str(task_id).strip()
    if s.isdigit():
        raise ValueError(
            "task_id must be a UUID string; legacy integer ids are not supported."
        )
    return s


def _task_satisfies_capabilities(
    required: Optional[list], worker_caps: Optional[list]
) -> bool:
    if not required:
        return True
    if worker_caps is None:
        return True
    return all(r in worker_caps for r in required)


def _task_satisfies_region(
    target_region: Optional[str], worker_region: Optional[str]
) -> bool:
    if not target_region:
        return True
    if not worker_region:
        return True
    return target_region.strip().lower() == worker_region.strip().lower()


def _is_agent_edge_compatible(agent_name: Any) -> bool:
    if not agent_name:
        return False
    try:
        from engine.edge_routing import is_agent_edge_compatible

        return is_agent_edge_compatible(agent_name)
    except Exception:
        return False


def _task_satisfies_worker_type(
    parsed: Dict[str, Any], worker_type: Optional[str]
) -> bool:
    if not worker_type or (worker_type or "").strip().lower() != "edge":
        return not _is_agent_edge_compatible(parsed.get("agent"))
    return _is_agent_edge_compatible(parsed.get("agent"))


def _row_to_task_dict(
    task_id: str, task_text: Any, created_at: Any, status: str
) -> Dict[str, Any]:
    parsed = parse_payload(task_text)
    out: Dict[str, Any] = {
        "id": task_id,
        "task": parsed["task"],
        "agent": parsed.get("agent"),
        "status": status,
        "created_at": created_at,
    }
    for k in (
        "runtime",
        "workflow_id",
        "node_id",
        "deps",
        "required_capabilities",
        "priority",
        "idempotency_key",
        "target_region",
        "agent_instance_id",
        "installation_id",
        "deployment_id",
        "input",
    ):
        if k in parsed:
            out[k] = parsed[k]
    return out


def _load_task_row(task_id: str) -> Optional[Dict[str, Any]]:
    try:
        return db.fetch_task_by_id(task_id)
    except ValueError:
        return None


def claim_task_running(task_id: str) -> Optional[Dict[str, Any]]:
    """Transition pending → running if eligible. Returns task dict or None."""
    row = db.claim_task_for_worker(task_id)
    if row is None:
        return None
    return _row_to_task_dict(
        str(row["id"]),
        row["task_text"],
        row["created_at"],
        str(row["status"]),
    )


def enqueue_task(
    task: Union[str, Dict[str, Any]],
    project_id: Optional[Union[str, uuid.UUID]] = None,
    user_region: Optional[str] = None,
) -> uuid.UUID:
    from config.production_guard import check_emergency_disable

    check_emergency_disable("enqueue")
    if isinstance(task, str):
        task = {"task": task}
    task = ensure_task_capabilities(task)
    if not task.get("target_region"):
        try:
            from engine.global_router import route_task as global_route_task

            target = global_route_task(task, user_region)
            if target:
                task = dict(task)
                task["target_region"] = target
        except Exception:
            pass
    task_text = serialize_payload(task)
    if project_id is not None:
        from services.quota_service import check_enqueue_quota

        check_enqueue_quota(project_id)

    task_id = db.create_task(
        task_text=task_text, status="queued", project_id=project_id
    )
    get_task_queue().enqueue_ready(task_id)
    if project_id is not None:
        try:
            from services.usage_metering import record_task_enqueued

            dep_id = None
            if isinstance(task, dict) and task.get("deployment_id"):
                dep_id = uuid.UUID(str(task["deployment_id"]))
            record_task_enqueued(
                project_id,
                task_id,
                deployment_id=dep_id,
                agent_name=task.get("agent") if isinstance(task, dict) else None,
            )
        except Exception:
            pass
    try:
        from agent_cloud.infra.observability.operational_log import emit_task_trace_event
        from config.redis_keys import REDIS_QUEUE_READY

        emit_task_trace_event(
            task_id,
            "enqueued",
            {
                "project_id": str(project_id) if project_id else None,
                "deployment_id": (
                    str(task.get("deployment_id")) if isinstance(task, dict) else None
                ),
                "queue_name": REDIS_QUEUE_READY,
                "runtime_version": (
                    task.get("runtime") if isinstance(task, dict) else None
                ),
            },
        )
    except Exception:
        pass
    return task_id


def push_existing_task(
    task_id: Union[int, str, uuid.UUID], _task_text: str | None = None
) -> None:
    """Re-queue an existing task by id (DAG / retries). Payload remains in Postgres."""
    get_task_queue().enqueue_ready(_task_id_str(task_id))


def fetch_next_task(
    block_timeout: Optional[int] = None,
    worker_capabilities: Optional[List[str]] = None,
    worker_region: Optional[str] = None,
    worker_type: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    BRPOP a task id, match worker filters, then claim pending → running in Postgres.
    """
    from config.settings import DEFAULT_BLOCK_TIMEOUT

    timeout = (
        block_timeout if block_timeout is not None else DEFAULT_BLOCK_TIMEOUT
    )
    q = get_task_queue()
    while True:
        raw = q.dequeue_raw_blocking(timeout)
        if raw is None:
            return None
        task_id = TaskQueue._parse_id(raw)
        if task_id is None:
            continue
        if task_id.isdigit():
            continue
        row = _load_task_row(str(task_id))
        if row is None:
            continue
        parsed = parse_payload(row.get("task_text"))
        if not _task_satisfies_worker_type(parsed, worker_type):
            q.lpush_raw(raw)
            continue
        if not _task_satisfies_region(parsed.get("target_region"), worker_region):
            q.lpush_raw(raw)
            continue
        if not _task_satisfies_capabilities(
            parsed.get("required_capabilities"), worker_capabilities
        ):
            q.lpush_raw(raw)
            continue
        claimed = claim_task_running(str(task_id))
        if claimed is None:
            continue
        return claimed


def update_task_status(task_id: Union[int, str, uuid.UUID], status: str) -> None:
    allowed = ("completed", "failed", "retry", "dead", "queued", "running")
    if status not in allowed:
        raise ValueError(f"status must be one of {allowed}")
    if status in ("completed", "failed"):
        db.update_task_status(_task_id_str(task_id), status)
        return
    tid = _task_id_str(task_id)
    from sqlalchemy import update as sa_update

    from database.models import Task, TaskStatus
    from database.session import SessionLocal

    try:
        st = TaskStatus(status)
    except ValueError as e:
        raise ValueError(f"invalid status: {status}") from e
    with SessionLocal() as session:
        session.execute(sa_update(Task).where(Task.id == uuid.UUID(tid)).values(status=st))
        session.commit()


def update_task_heartbeat(task_id: Union[int, str, uuid.UUID]) -> None:
    db.update_task_heartbeat(_task_id_str(task_id))
