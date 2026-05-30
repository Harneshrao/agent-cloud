"""
Event engine: matches incoming events to triggers and enqueues tasks.

When an event is received:
1. Find enabled triggers with matching event_type.
2. Generate task text from task_template (substitute {{key}} from payload).
3. Enqueue the task (with optional agent).
"""

from __future__ import annotations

import re
import uuid
from typing import Any, Dict, List, Optional

from database.event_triggers import list_enabled_by_event_type
from services.task_service import enqueue_task


def _render_template(template: str, payload: Dict[str, Any]) -> str:
    """Replace {{key}} in template with payload.get(key, '')."""
    if not payload:
        return template
    result = template
    for key, value in payload.items():
        placeholder = "{{" + str(key) + "}}"
        result = result.replace(placeholder, str(value) if value is not None else "")
    # Remove any remaining {{...}} that weren't in payload.
    result = re.sub(r"\{\{[^}]+\}\}", "", result)
    return result.strip()


def process_event(
    event_type: str,
    payload: Dict[str, Any],
    project_id: Optional[uuid.UUID] = None,
    source: str = "user",
) -> List[uuid.UUID]:
    """
    Process an incoming event: find matching triggers, render task_template with payload,
    enqueue each task. Returns list of enqueued task IDs.
    project_id is optional for multi-tenant scoping.
    source: "user" (default) or "agent" — only triggers that match this source (or "any") fire.
    """
    triggers = list_enabled_by_event_type(event_type, project_id=project_id, source=source)
    task_ids = []
    for t in triggers:
        task_text = _render_template(t.get("task_template") or "", payload)
        if not task_text:
            continue
        agent = t.get("agent")
        if agent:
            enqueued_id = enqueue_task({"task": task_text, "agent": agent}, project_id=project_id)
        else:
            enqueued_id = enqueue_task(task_text, project_id=project_id)
        task_ids.append(enqueued_id)
    return task_ids
