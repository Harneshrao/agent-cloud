"""
Task recovery: find running tasks with stale heartbeat, reset to pending and requeue.

Runs independently of workers. Background loop every 30 seconds.
Stalled = running and last_heartbeat < now - 60 seconds (or null).
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, List, Tuple

from database.db import db

# Last N entries for GET /system/recovery
_MAX_RECORDS = 100
_stalled_tasks: List[Dict[str, Any]] = []
_recovered_tasks: List[Dict[str, Any]] = []
_lock = threading.Lock()

# Stale threshold: treat running task as stalled if no heartbeat for this many seconds
STALE_HEARTBEAT_SECONDS = 60
RECOVERY_INTERVAL_SECONDS = 30


def run_recovery_once() -> Tuple[List[int], List[int]]:
    """
    Find running tasks with last_heartbeat older than 60s (or null),
    set status to 'pending', clear last_heartbeat.
    Returns (stalled_task_ids, recovered_task_ids).
    """
    rows = db.get_stalled_running_tasks(stale_seconds=STALE_HEARTBEAT_SECONDS)
    stalled_ids = [int(r["id"]) for r in rows]
    recovered_ids = []
    for task_id in stalled_ids:
        try:
            db.reset_task_to_pending(task_id)
            recovered_ids.append(task_id)
        except Exception:
            pass
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with _lock:
        for tid in stalled_ids:
            _stalled_tasks.append({"task_id": tid, "detected_at": now_iso})
            if len(_stalled_tasks) > _MAX_RECORDS:
                _stalled_tasks.pop(0)
        for tid in recovered_ids:
            _recovered_tasks.append({"task_id": tid, "recovered_at": now_iso})
            if len(_recovered_tasks) > _MAX_RECORDS:
                _recovered_tasks.pop(0)
    return (stalled_ids, recovered_ids)


def run_recovery_loop() -> None:
    """Run recovery every RECOVERY_INTERVAL_SECONDS. Intended for a daemon thread."""
    while True:
        time.sleep(RECOVERY_INTERVAL_SECONDS)
        try:
            run_recovery_once()
        except Exception:
            pass


def get_recovery_state() -> Dict[str, Any]:
    """Return stalled_tasks and recovered_tasks for GET /system/recovery."""
    with _lock:
        return {
            "stalled_tasks": list(_stalled_tasks),
            "recovered_tasks": list(_recovered_tasks),
        }


def start_recovery_background() -> None:
    """Start the recovery loop in a daemon thread."""
    t = threading.Thread(target=run_recovery_loop, daemon=True)
    t.start()
