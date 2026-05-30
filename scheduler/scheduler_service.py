"""
Scheduler service: evaluates cron expressions and enqueues tasks when due.

Runs a loop that reads enabled scheduled_tasks, evaluates cron_expression,
and enqueues tasks via the task queue when the schedule triggers.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import Optional

from database.scheduled_tasks import list_enabled, update_last_run
from services.task_service import enqueue_task

try:
    from croniter import croniter
except ImportError:
    croniter = None  # type: ignore

# How often the scheduler wakes up to check (seconds).
TICK_INTERVAL = 60


def _should_trigger(
    cron_expression: str,
    last_run_at: Optional[datetime],
    created_at: Optional[datetime],
    now: datetime,
) -> bool:
    """Return True if the schedule should run at or before now."""
    if croniter is None:
        return False
    # Base for "next run": last run, or creation time, or past so first run can trigger.
    base = last_run_at or created_at or (now - timedelta(days=1))
    it = croniter(cron_expression, base)
    next_run = it.get_next(datetime)
    return next_run <= now


def _enqueue_scheduled(schedule: dict) -> None:
    """Enqueue one scheduled task (payload with task and optional agent)."""
    task_text = schedule.get("task_text") or ""
    agent = schedule.get("agent")
    project_id = schedule.get("project_id")
    if agent:
        enqueue_task({"task": task_text, "agent": agent}, project_id=project_id)
    else:
        enqueue_task(task_text, project_id=project_id)


def _run_agent_schedules_tick(now: datetime) -> None:
    """Check agent_schedules (user-installed agent automation); enqueue run_agent tasks when due."""
    try:
        from database.agent_schedules import list_active_schedules, update_last_run
        from database.agent_installations import get_installation
        for s in list_active_schedules():
            cron_expr = s.get("cron_expression")
            if not cron_expr or croniter is None:
                continue
            last_run = s.get("last_run_at")
            if isinstance(last_run, str):
                try:
                    last_run = datetime.fromisoformat(last_run.replace("Z", "+00:00"))
                except Exception:
                    last_run = None
            created_at = s.get("created_at")
            if isinstance(created_at, str):
                try:
                    created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                except Exception:
                    created_at = None
            if not _should_trigger(cron_expr, last_run, created_at, now):
                continue
            inst = get_installation(s["installation_id"])
            if inst is None or inst.get("status") != "active":
                continue
            config = inst.get("configuration") or {}
            payload = {
                "agent": inst["agent_name"],
                "task": "Run with configured inputs",
                "input": config,
                "installation_id": s["installation_id"],
                "project_id": inst["project_id"],
            }
            enqueue_task(payload, project_id=inst["project_id"])
            update_last_run(s["schedule_id"], now)
    except Exception:
        pass


def run_tick(now: Optional[datetime] = None) -> None:
    """
    Run one scheduler tick: load enabled schedules, evaluate cron, enqueue due tasks.
    Also processes agent_schedules (user-installed agent automation).
    """
    if now is None:
        now = datetime.utcnow()
    _run_agent_schedules_tick(now)
    for s in list_enabled():
        cron_expr = s.get("cron_expression")
        if not cron_expr:
            continue
        last_run = s.get("last_run_at")
        if isinstance(last_run, str):
            try:
                last_run = datetime.fromisoformat(last_run.replace("Z", "+00:00"))
            except Exception:
                last_run = None
        created_at = s.get("created_at")
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except Exception:
                created_at = None
        if _should_trigger(cron_expr, last_run, created_at, now):
            _enqueue_scheduled(s)
            update_last_run(s["id"], now)


def run_loop(tick_interval: int = TICK_INTERVAL) -> None:
    """
    Main scheduler loop: every tick_interval seconds, run a tick.
    Runs until interrupted.
    """
    if croniter is None:
        raise RuntimeError("croniter is required for the scheduler. Install with: pip install croniter")
    while True:
        try:
            run_tick()
        except Exception:
            pass  # Log and continue
        time.sleep(tick_interval)


def start_scheduler(tick_interval: int = 30) -> None:
    """
    Entry point: run the scheduler as a long-lived service.
    Loads agent schedules, checks cron expressions, enqueues tasks when due.
    Runs indefinitely until interrupted (e.g. Ctrl+C).
    """
    print("Scheduler service started")
    if croniter is None:
        print("Scheduler error: croniter is required. Install with: pip install croniter")
        return
    while True:
        try:
            print("Checking schedules...")
            run_tick()
        except Exception as e:
            print("Scheduler error:", e)
        time.sleep(tick_interval)


if __name__ == "__main__":
    start_scheduler()
