"""
Workflow Controller: manages task execution and workflow state.

- Monitors task_graph status.
- Detects when subtasks complete and updates parent when all children are done.
- Retries failed tasks up to a configurable limit.
- Provides workflow-level status (running, completed, failed).
"""

from __future__ import annotations

from typing import Optional

from database.db import db
from database.task_graph import (
    get_children,
    get_row,
    increment_retry_count,
    insert_link,
    update_status,
)
from task_queue.task_queue import enqueue_task

# Maximum retries for a failed task before giving up.
MAX_RETRIES = 3


def check_task_completion(task_id: int) -> None:
    """
    Called after a task finishes successfully.
    Updates this task's status to 'completed' in task_graph, then checks whether
    its parent has all children completed and updates the parent's status if so.
    """
    row = get_row(task_id)
    if row is not None:
        update_status(task_id, "completed")

    parent_id = row.get("parent_task_id") if row is not None else None
    if parent_id is None:
        return

    children = get_children(parent_id)
    if not children:
        return
    if all(c.get("status") == "completed" for c in children):
        update_status(parent_id, "completed")
        # Recursively check if parent's parent is now complete.
        check_task_completion(parent_id)


def handle_task_failure(task_id: int) -> None:
    """
    Called when a task fails. Updates task_graph status to 'failed'.
    Optionally retries the task if retry_count is below MAX_RETRIES.
    """
    row = get_row(task_id)
    if row is not None:
        update_status(task_id, "failed")
    retry_task(task_id)


def retry_task(task_id: int) -> Optional[int]:
    """
    Re-enqueue the task for retry if retry_count < MAX_RETRIES.
    Reads the original task payload from the tasks table, enqueues it again,
    and records the new link in task_graph with incremented retry_count.
    Returns the new task_id if retried, None if max retries exceeded or task not in graph.
    """
    row = get_row(task_id)
    if row is None:
        return None
    current_retry = int(row.get("retry_count") or 0)
    if current_retry >= MAX_RETRIES:
        return None

    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT task_text FROM tasks WHERE id = ?", (task_id,))
    task_row = cur.fetchone()
    if task_row is None:
        return None
    task_text = task_row["task_text"]
    parent_task_id = row["parent_task_id"]

    new_task_id = enqueue_task(task_text)
    insert_link(
        task_id=new_task_id,
        parent_task_id=parent_task_id,
        status="pending",
        retry_count=current_retry + 1,
    )
    return new_task_id


def get_workflow_status(task_id: int) -> str:
    """
    Return workflow-level status for a task: 'running', 'completed', or 'failed'.
    If the task has a row in task_graph, return its status; otherwise 'completed'.
    """
    row = get_row(task_id)
    if row is None:
        return "completed"
    return row.get("status") or "running"
