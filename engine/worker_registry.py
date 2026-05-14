"""
Worker registry: register workers, capabilities, and record heartbeats for observability.

Workers call register_worker on startup and optionally set_capabilities for
resource-aware scheduling. Heartbeat every ~10 seconds with tasks_running.
"""

from __future__ import annotations

from typing import List

from database.workers import heartbeat as db_heartbeat
from database.workers import register_worker as db_register_worker
from database.workers import get_worker_region as db_get_worker_region
from database.workers import get_worker_type as db_get_worker_type
from database.worker_capabilities import set_capabilities as db_set_capabilities
from database.worker_capabilities import get_capabilities as db_get_capabilities


def register_worker(worker_id: str, region: str | None = None, worker_type: str | None = None) -> None:
    """
    Register a worker on startup. Idempotent; safe to call multiple times.
    region: optional geographic region (e.g. us, eu, asia).
    worker_type: optional type (e.g. 'edge' for edge workers running lightweight agents).
    """
    db_register_worker(worker_id, region=region, worker_type=worker_type)


def set_capabilities(worker_id: str, capabilities: List[str]) -> None:
    """
    Advertise worker capabilities (e.g. python, gpu, browser) for task scheduling.
    Call after register_worker. Replaces any existing capability set.
    """
    db_set_capabilities(worker_id, capabilities)


def get_capabilities(worker_id: str) -> List[str]:
    """Return the list of capabilities advertised by the worker."""
    return db_get_capabilities(worker_id)


def heartbeat(worker_id: str, tasks_running: int = 0, region: str | None = None, worker_type: str | None = None) -> None:
    """
    Update worker heartbeat (last_seen and tasks_running).
    Call periodically (e.g. every 10 seconds). Registers the worker if not present.
    region / worker_type: optional; updates stored values when provided.
    """
    db_heartbeat(worker_id, tasks_running, region=region, worker_type=worker_type)


def get_region(worker_id: str) -> str | None:
    """Return the worker's region, or None if not set."""
    return db_get_worker_region(worker_id)


def get_worker_type(worker_id: str) -> str | None:
    """Return the worker's type (e.g. 'edge'), or None if not set."""
    return db_get_worker_type(worker_id)
