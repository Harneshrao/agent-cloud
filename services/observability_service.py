"""Project-scoped operational visibility."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from database import deployment_store
from database.task_observability import (
    build_task_trace,
    get_task_detail,
    list_agent_runs_for_task,
    list_dlq_for_project,
    list_task_events,
    list_task_logs,
    list_tasks_for_project,
    queue_snapshot,
    task_counts_for_project,
)
from database.workers import count_active_workers, get_all_workers
from engine.alerting import evaluate_alerts
from engine.metrics_collector import get_tasks_per_second


def assert_task_in_project(task_id: uuid.UUID, project_id: uuid.UUID) -> Dict[str, Any]:
    detail = get_task_detail(task_id)
    if detail is None:
        raise ValueError("task not found")
    if detail["project_id"] != str(project_id):
        raise ValueError("task not in project")
    return detail


def get_platform_health() -> Dict[str, Any]:
    """Lightweight health for developers (no admin required)."""
    db_ok = False
    redis_ok = False
    try:
        from database.db import db

        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        db_ok = True
    except Exception:
        pass
    try:
        queue_snapshot()
        redis_ok = True
    except Exception:
        pass
    return {
        "database": "ok" if db_ok else "error",
        "redis": "ok" if redis_ok else "error",
        "workers_active": count_active_workers(within_seconds=30),
        "tasks_per_second": round(get_tasks_per_second(60), 4),
    }


def get_deployment_timeline(
    project_id: uuid.UUID, deployment_id: uuid.UUID
) -> Dict[str, Any]:
    dep = deployment_store.get_deployment_for_project(deployment_id, project_id)
    if dep is None:
        raise ValueError("deployment not found")
    events = deployment_store.list_deployment_events(deployment_id)
    health = None
    try:
        from agent_cloud.core.deployments.pipeline import get_deployment_health

        health = get_deployment_health(deployment_id)
    except Exception:
        pass
    related_tasks = list_tasks_for_project(project_id, limit=20)
    related = [
        t
        for t in related_tasks
        if t.get("deployment_id") == str(deployment_id)
    ]
    return {
        "deployment": dep,
        "events": events,
        "health": health,
        "recent_tasks": related,
    }


def classify_incidents(queue: Dict[str, Any], project_stats: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Rule-based incident hints (no paging integration)."""
    incidents: List[Dict[str, Any]] = []
    if queue.get("queue_ready", 0) > 500:
        incidents.append(
            {
                "severity": "warning",
                "code": "queue_backlog",
                "message": f"Ready queue depth is {queue['queue_ready']}",
            }
        )
    if queue.get("visibility_stale_count", 0) > 10:
        incidents.append(
            {
                "severity": "warning",
                "code": "stale_visibility",
                "message": f"{queue['visibility_stale_count']} tasks past visibility deadline",
            }
        )
    if project_stats.get("failure_rate", 0) > 0.25 and project_stats.get("total", 0) >= 5:
        incidents.append(
            {
                "severity": "critical",
                "code": "high_failure_rate",
                "message": f"Failure rate {project_stats['failure_rate']:.0%} in last {project_stats['hours']}h",
            }
        )
    try:
        for alert in evaluate_alerts():
            incidents.append(
                {
                    "severity": alert.get("severity", "warning"),
                    "code": alert.get("type", "platform_alert"),
                    "message": alert.get("message", ""),
                }
            )
    except Exception:
        pass
    return incidents
