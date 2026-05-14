"""Postgres implementation of `core.tasks.ports.TaskRepository`."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import update

from agent_cloud.core.tasks.enums import TaskLifecycle
from agent_cloud.core.tasks.models import Task as TaskDomain
from agent_cloud.core.tasks.ports import TaskRepository
from database.db import db
from database.models import Task as TaskORM
from database.models import TaskStatus
from database.session import SessionLocal


def _to_domain(row: TaskORM) -> TaskDomain:
    return TaskDomain(
        id=row.id,
        project_id=row.project_id,
        status=TaskLifecycle(row.status.value),
        payload=row.input_json if isinstance(row.input_json, dict) else {},
        retries=row.retry_count,
        max_retries=row.max_retries,
    )


class PostgresTaskRepository(TaskRepository):
    """Maps ORM `Task` rows to domain `Task` models."""

    def create_queued(
        self,
        payload: dict[str, Any],
        project_id: UUID,
        *,
        idempotency_key: str | None,
    ) -> UUID:
        tid = db.create_task(
            task_text=payload,
            status="queued",
            project_id=project_id,
        )
        if idempotency_key:
            with SessionLocal() as session:
                t = session.get(TaskORM, tid)
                if t is not None:
                    t.idempotency_key = idempotency_key
                    session.commit()
        return tid

    def try_claim(
        self, task_id: UUID, worker_id: str | None
    ) -> TaskDomain | None:
        row = db.claim_task_for_worker(task_id)
        if row is None:
            return None
        with SessionLocal() as session:
            orm = session.get(TaskORM, task_id)
            if orm is None:
                return None
            session.expunge(orm)
        return _to_domain(orm)

    def mark_completed(self, task_id: UUID, result: dict[str, Any]) -> None:
        db.store_result(task_id, result)

    def mark_failed(self, task_id: UUID) -> None:
        db.update_task_status(task_id, "failed")

    def mark_retry(self, task_id: UUID, *, retries: int) -> None:
        with SessionLocal() as session:
            session.execute(
                update(TaskORM)
                .where(TaskORM.id == task_id)
                .values(status=TaskStatus.retry, retry_count=retries)
            )
            session.commit()

    def mark_dead(self, task_id: UUID, reason: str) -> None:
        db.update_task_status(task_id, "dead")
        # Optional: insert into dead_letter_queue via infra helper when wired.
