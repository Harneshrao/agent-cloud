"""
Task Manager: maintains subtasks and pushes them to the task queue.
Records parent-child relationships in the task graph.

Agents may return {"result": "...", "subtasks": ["subtask 1", "subtask 2"]}.
Subtasks are enqueued with parent_task metadata and linked in task_graph.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from database.task_graph import insert_link
from services.task_service import enqueue_task


def enqueue_subtasks(
    parent_task: str,
    subtasks: List[str],
    agent: Optional[str] = None,
    parent_task_id: Optional[int] = None,
) -> List[int]:
    """
    Enqueue each subtask into the task queue with parent_task set to parent_task.
    If parent_task_id is provided, records each new task in the task_graph.
    Returns a list of task IDs for the enqueued subtasks.
    """
    if not subtasks:
        return []
    ids = []
    for st in subtasks:
        if not isinstance(st, str) or not st.strip():
            continue
        payload: Dict[str, Any] = {
            "task": st.strip(),
            "parent_task": parent_task,
        }
        if agent is not None:
            payload["agent"] = agent
        new_task_id = enqueue_task(payload)
        ids.append(new_task_id)
        if parent_task_id is not None:
            insert_link(task_id=new_task_id, parent_task_id=parent_task_id, status="pending")
    return ids


def collect_subtasks_from_output(output: Any) -> List[str]:
    """
    Extract subtasks from an agent output. Returns a list of task strings.
    Handles output like {"result": "...", "subtasks": ["a", "b"]}.
    """
    if not isinstance(output, dict):
        return []
    raw = output.get("subtasks")
    if not isinstance(raw, list):
        return []
    return [str(s).strip() for s in raw if s and str(s).strip()]
