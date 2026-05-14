"""
PostgreSQL — UUID task schema only (SQLAlchemy ORM).

Apply schema with: alembic upgrade head
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional, Union

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from config.settings import DEFAULT_PROJECT_UUID
from database.models import AgentRun, AgentRunStatus, Result, Task, TaskStatus
from database.pg_compat import CompatConnection
from database.session import SessionLocal, engine


def _normalize_input(task_text: Union[str, dict[str, Any]]) -> dict[str, Any]:
    if isinstance(task_text, dict):
        return task_text
    s = str(task_text).strip()
    if s.startswith("{"):
        try:
            return json.loads(s)
        except (json.JSONDecodeError, TypeError):
            pass
    return {"task": s}


def _status_from_str(s: str) -> TaskStatus:
    try:
        return TaskStatus(s)
    except ValueError:
        return TaskStatus.pending


def _task_row_proxy(t: Task) -> dict[str, Any]:
    return {
        "id": t.id,
        "task_text": json.dumps(t.input_json) if t.input_json else "",
        "status": t.status.value,
        "created_at": t.created_at,
        "project_id": t.project_id,
        "input_json": t.input_json,
    }


def _project_uuid(project_id: Optional[Union[str, uuid.UUID]]) -> uuid.UUID:
    if project_id is None:
        return uuid.UUID(DEFAULT_PROJECT_UUID)
    if isinstance(project_id, uuid.UUID):
        return project_id
    s = str(project_id).strip()
    try:
        return uuid.UUID(s)
    except ValueError as e:
        raise ValueError("project_id must be a UUID string") from e


class Database:
    """Tasks / results / agent_runs — UUID only."""

    def __init__(self) -> None:
        self._engine = engine
        self._compat_conn: Optional[CompatConnection] = None

    def get_engine(self):
        return self._engine

    def get_connection(self) -> CompatConnection:
        """Legacy raw SQL (? placeholders). One long-lived connection per process."""
        if self._compat_conn is None:
            self._compat_conn = CompatConnection(self._engine.raw_connection())
        return self._compat_conn

    def session(self) -> Session:
        return SessionLocal()

    def _project_uuid(
        self, project_id: Optional[Union[str, uuid.UUID]]
    ) -> uuid.UUID:
        return _project_uuid(project_id)

    def _task_uuid(self, task_id: Union[str, uuid.UUID]) -> uuid.UUID:
        if isinstance(task_id, uuid.UUID):
            return task_id
        s = str(task_id).strip()
        if s.isdigit():
            raise ValueError(
                "task_id must be a UUID; legacy integer ids are not supported."
            )
        return uuid.UUID(s)

    def create_task(
        self,
        task_text: Union[str, dict[str, Any]],
        status: str = "pending",
        project_id: Optional[Union[str, uuid.UUID]] = None,
    ) -> uuid.UUID:
        inp = _normalize_input(task_text)
        st = _status_from_str(status)
        pid = self._project_uuid(project_id)
        with SessionLocal() as session:
            task = Task(project_id=pid, status=st, input_json=inp)
            session.add(task)
            session.commit()
            session.refresh(task)
            return task.id

    def fetch_task_by_id(
        self, task_id: Union[str, uuid.UUID]
    ) -> Optional[dict[str, Any]]:
        tid = self._task_uuid(task_id)
        with SessionLocal() as session:
            t = session.get(Task, tid)
            return _task_row_proxy(t) if t else None

    def claim_task_for_worker(
        self, task_id: Union[str, uuid.UUID]
    ) -> Optional[dict[str, Any]]:
        """queued / retry / pending → running; returns row dict or None if lost race."""
        tid = self._task_uuid(task_id)
        now = datetime.now(timezone.utc)
        wid = (os.environ.get("WORKER_ID") or "").strip() or None
        with SessionLocal() as session:
            task = session.execute(
                select(Task)
                .where(
                    Task.id == tid,
                    or_(
                        Task.status == TaskStatus.pending,
                        Task.status == TaskStatus.queued,
                        Task.status == TaskStatus.retry,
                    ),
                )
                .with_for_update()
            ).scalar_one_or_none()
            if task is None:
                session.commit()
                return None
            task.status = TaskStatus.running
            task.last_heartbeat = now
            task.started_at = now
            task.worker_id = wid
            session.commit()
            session.refresh(task)
            return _task_row_proxy(task)

    def update_task_status(
        self, task_id: Union[str, uuid.UUID], status: str
    ) -> None:
        tid = self._task_uuid(task_id)
        st = _status_from_str(status)
        now = datetime.now(timezone.utc)
        with SessionLocal() as session:
            vals: dict[str, Any] = {"status": st}
            if st in (TaskStatus.completed, TaskStatus.failed, TaskStatus.dead):
                vals["completed_at"] = now
            session.execute(update(Task).where(Task.id == tid).values(**vals))
            session.commit()

    def update_task_heartbeat(self, task_id: Union[str, uuid.UUID]) -> None:
        tid = self._task_uuid(task_id)
        with SessionLocal() as session:
            session.execute(
                update(Task)
                .where(Task.id == tid)
                .values(last_heartbeat=datetime.now(timezone.utc))
            )
            session.commit()

    def get_stalled_running_tasks(self, stale_seconds: int = 60):
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=stale_seconds)
        with SessionLocal() as session:
            rows = (
                session.execute(
                    select(Task).where(
                        Task.status == TaskStatus.running,
                        (Task.last_heartbeat.is_(None))
                        | (Task.last_heartbeat < cutoff),
                    )
                )
                .scalars()
                .all()
            )
            return [_task_row_proxy(t) for t in rows]

    def reset_task_to_pending(self, task_id: Union[str, uuid.UUID]) -> None:
        """Re-queue path: set status to queued and clear worker lease fields."""
        tid = self._task_uuid(task_id)
        with SessionLocal() as session:
            session.execute(
                update(Task)
                .where(Task.id == tid)
                .values(
                    status=TaskStatus.queued,
                    last_heartbeat=None,
                    worker_id=None,
                    started_at=None,
                )
            )
            session.commit()

    def get_pending_tasks(self):
        with SessionLocal() as session:
            rows = (
                session.execute(
                    select(Task)
                    .where(Task.status == TaskStatus.pending)
                    .order_by(Task.created_at.asc())
                )
                .scalars()
                .all()
            )
            return [_task_row_proxy(t) for t in rows]

    def get_task_project_id(
        self, task_id: Union[str, uuid.UUID]
    ) -> Optional[uuid.UUID]:
        tid = self._task_uuid(task_id)
        with SessionLocal() as session:
            task = session.get(Task, tid)
            return task.project_id if task else None

    def store_result(self, task_id: Union[str, uuid.UUID], result: Any) -> None:
        tid = self._task_uuid(task_id)
        now = datetime.now(timezone.utc)
        with SessionLocal() as session:
            task = session.get(Task, tid)
            if task is None:
                return
            if isinstance(result, dict):
                task.output_json = result
            else:
                task.output_json = {"result": result}
            task.status = TaskStatus.completed
            task.completed_at = now
            session.commit()

    def store_agent_run(
        self,
        task_id: Union[str, uuid.UUID],
        agent_name: str,
        output: Any,
    ) -> uuid.UUID:
        tid = self._task_uuid(task_id)
        with SessionLocal() as session:
            run = AgentRun(
                task_id=tid,
                agent_name=agent_name,
                status=AgentRunStatus.completed,
                output=output if isinstance(output, dict) else {"data": output},
            )
            session.add(run)
            session.commit()
            session.refresh(run)
            return run.id


db = Database()
