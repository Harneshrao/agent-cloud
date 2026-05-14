"""
Task routing is handled by Redis BRPOP + Postgres claim in the worker.

The legacy in-memory pool and background poller are removed. Optional HTTP
compatibility: GET /scheduler/task returns no task (use Redis workers only).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def get_next_task(
    worker_id: str,
    worker_capabilities: Optional[List[str]] = None,
    worker_region: Optional[str] = None,
    worker_type: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Deprecated: workers pull work via Redis; scheduler HTTP always empty."""
    return None


def pool_size() -> int:
    return 0


def start_scheduler_background(poll_timeout: int = 30) -> None:
    """No-op: legacy hook removed."""
    return None
