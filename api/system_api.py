"""
System Metrics API: observability and control plane.

Exposes queue metrics, worker status, container pool state, workflow metrics,
region metrics, worker health, and alerts. Read-only.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Any, Dict

from fastapi import APIRouter, Depends, Query

from api.deps import require_admin
from config.settings import REDIS_QUEUE_READY as TASKS_QUEUE_KEY, REDIS_URL
from database.db import db
from database.workers import count_active_workers, get_all_workers
from database.dead_letter import list_dead_letters
from engine.autoscaler import get_autoscaler_state
from engine.task_recovery import get_recovery_state
from engine.metrics_collector import (
    _get_redis_queue_length,
    get_tasks_per_second,
    get_queue_length_per_region,
    get_worker_utilization,
    get_workflow_success_rate,
    get_region_metrics,
    get_worker_health,
)
from engine.alerting import evaluate_alerts

router = APIRouter(prefix="/system", tags=["system"])

ACTIVE_WORKER_THRESHOLD_SEC = 30


def _get_queue_length() -> int:
    """Return current length of the Redis task queue."""
    return _get_redis_queue_length()


def _get_tasks_running() -> int:
    """Count tasks with status 'running' in the tasks table."""
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS n FROM tasks WHERE status = ?", ("running",))
    row = cur.fetchone()
    return row["n"] if row else 0


def _get_tasks_failed_last_hour() -> int:
    """Count tasks with status 'failed' and created_at in the last hour."""
    conn = db.get_connection()
    cur = conn.cursor()
    since = (datetime.utcnow() - timedelta(hours=1))
    cur.execute(
        "SELECT COUNT(*) AS n FROM tasks WHERE status = ? AND created_at >= ?",
        ("failed", since),
    )
    row = cur.fetchone()
    return row["n"] if row else 0


def _get_container_pool_metrics() -> Dict[str, Any]:
    """Read idle/busy counts from the container pool singleton."""
    try:
        from engine.container_pool import get_pool
        pool = get_pool()
        idle = pool.idle_containers
        busy = pool.busy_containers
        return {
            "containers_idle": len(idle),
            "containers_busy": len(busy),
            "idle_ids": idle,
            "busy_ids": busy,
        }
    except Exception:
        return {"containers_idle": 0, "containers_busy": 0, "idle_ids": [], "busy_ids": []}


@router.get("/metrics")
def get_system_metrics(admin=Depends(require_admin)) -> Dict[str, Any]:
    """
    Aggregate system metrics: queue, workers, containers, tasks, workflows,
    regions (us, eu, asia), worker health, and throughput.
    """
    pool = _get_container_pool_metrics()
    queue_length = _get_queue_length()
    workers_active = count_active_workers(within_seconds=ACTIVE_WORKER_THRESHOLD_SEC)
    utilization = get_worker_utilization()
    regions = get_region_metrics()
    health = get_worker_health()
    return {
        "queue_length": queue_length,
        "queue_length_per_region": get_queue_length_per_region(),
        "workers_active": workers_active,
        "containers_idle": pool["containers_idle"],
        "containers_busy": pool["containers_busy"],
        "tasks_running": _get_tasks_running(),
        "tasks_failed_last_hour": _get_tasks_failed_last_hour(),
        "tasks_per_second": round(get_tasks_per_second(60), 4),
        "worker_utilization": utilization,
        "workflow_success_rate_last_hour": round(get_workflow_success_rate(60), 4),
        "regions": regions,
        "worker_health": health,
    }


@router.get("/health")
def get_system_health(admin=Depends(require_admin)) -> Dict[str, Any]:
    """
    Lightweight health check for core subsystems: database, redis, workers, docker_runtime, storage, dependency_cache.
    """
    # Database
    try:
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        db_status = "ok"
    except Exception:
        db_status = "error"

    # Redis
    try:
        _ = _get_redis_queue_length()
        redis_status = "ok"
    except Exception:
        redis_status = "error"

    # Workers
    try:
        workers_active = count_active_workers(within_seconds=ACTIVE_WORKER_THRESHOLD_SEC)
    except Exception:
        workers_active = 0

    # Docker runtime
    try:
        from agent_runtime.docker_executor import use_docker_runtime
        docker_runtime = bool(use_docker_runtime())
    except Exception:
        docker_runtime = False

    # Storage and dependency cache
    try:
        from agent_runtime.storage_paths import get_storage_root
        root = get_storage_root()
        root.mkdir(parents=True, exist_ok=True)
        storage_status = "ok"
    except Exception:
        storage_status = "error"
    try:
        from agent_runtime.dependency_cache import get_dependency_cache_root
        cache_root = get_dependency_cache_root()
        cache_root.mkdir(parents=True, exist_ok=True)
        dep_cache_status = "ok"
    except Exception:
        dep_cache_status = "error"

    return {
        "database": db_status,
        "redis": redis_status,
        "workers": workers_active,
        "docker_runtime": docker_runtime,
        "storage": storage_status,
        "dependency_cache": dep_cache_status,
        "worker_health": get_worker_health(),
    }


@router.get("/workers")
def get_system_workers(admin=Depends(require_admin)) -> Dict[str, Any]:
    """List all registered workers and their last_seen, tasks_running, status."""
    workers = get_all_workers()
    return {"workers": workers, "count": len(workers)}


@router.get("/queue")
def get_system_queue(admin=Depends(require_admin)) -> Dict[str, Any]:
    """Queue metrics from Redis."""
    return {
        "queue_key": TASKS_QUEUE_KEY,
        "queue_length": _get_queue_length(),
    }


@router.get("/containers")
def get_system_containers(admin=Depends(require_admin)) -> Dict[str, Any]:
    """Container pool state: idle and busy container counts and ids."""
    return _get_container_pool_metrics()


@router.get("/recovery")
def get_system_recovery(admin=Depends(require_admin)) -> Dict[str, Any]:
    """Task recovery monitoring: recently stalled and recovered task ids."""
    return get_recovery_state()


@router.get("/autoscaler")
def get_system_autoscaler(admin=Depends(require_admin)) -> Dict[str, Any]:
    """Autoscaler state: active_workers, queue_length, scaling_actions."""
    return get_autoscaler_state()


@router.get("/dead_letters")
def get_system_dead_letters(limit: int = Query(100, ge=1, le=500), admin=Depends(require_admin)) -> Dict[str, Any]:
    """List tasks that exceeded retry limit and were moved to the dead letter queue (for inspection)."""
    items = list_dead_letters(limit=limit)
    return {"dead_letters": items, "count": len(items)}


@router.get("/alerts")
def get_system_alerts() -> Dict[str, Any]:
    """Evaluate and return active alerts: queue backlog spikes, worker crash loops, high failure rate."""
    alerts = evaluate_alerts()
    return {"alerts": alerts, "count": len(alerts)}
