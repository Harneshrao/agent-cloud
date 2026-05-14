"""
In-memory store for streaming agent execution events.

Allows the API to retrieve incremental updates (progress, data chunks) emitted by agents
during execution. Events are keyed by task_id.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Union

_store: Dict[str, List[Dict[str, Any]]] = {}


def _task_key(task_id: Union[int, str, uuid.UUID]) -> str:
    return str(task_id)


def append_event(task_id: Union[int, str, uuid.UUID], event: Dict[str, Any]) -> None:
    """Append a stream event for the given task. Event is stored in memory."""
    k = _task_key(task_id)
    if k not in _store:
        _store[k] = []
    _store[k].append(dict(event))


def get_events(task_id: Union[int, str, uuid.UUID]) -> List[Dict[str, Any]]:
    """Return all events for the task, in order. Returns empty list if none."""
    return list(_store.get(_task_key(task_id), []))
