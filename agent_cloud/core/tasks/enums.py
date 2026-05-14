"""Domain task lifecycle (mirror DB enum names for consistency)."""

from __future__ import annotations

from enum import StrEnum


class TaskLifecycle(StrEnum):
    pending = "pending"
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    retry = "retry"
    dead = "dead"
    workflow_root = "workflow_root"
