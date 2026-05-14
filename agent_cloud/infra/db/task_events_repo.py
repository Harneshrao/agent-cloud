"""Append-only task_events for observability (Postgres truth)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from database.models import TaskEvent
from database.session import SessionLocal


def emit_task_event(
    task_id: uuid.UUID,
    event_type: str,
    payload: dict[str, Any] | None = None,
    *,
    session: Session | None = None,
) -> uuid.UUID:
    """Insert a task event; returns event id."""

    def _insert(s: Session) -> uuid.UUID:
        ev = TaskEvent(
            task_id=task_id,
            event_type=event_type,
            payload=payload or {},
        )
        s.add(ev)
        s.commit()
        s.refresh(ev)
        return ev.id

    if session is None:
        with SessionLocal() as s:
            return _insert(s)
    return _insert(session)
