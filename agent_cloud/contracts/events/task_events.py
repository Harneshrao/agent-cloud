"""Task lifecycle event names (contracts for task_events table / observability)."""

from __future__ import annotations

from enum import StrEnum


class TaskEventType(StrEnum):
    enqueued = "enqueued"
    claimed = "claimed"
    completed = "completed"
    failed = "failed"
    retry_scheduled = "retry_scheduled"
    dead_lettered = "dead_lettered"
    visibility_recovered = "visibility_recovered"
