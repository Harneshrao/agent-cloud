"""
Global observability: metrics aggregation for workers, regions, tasks, workflows.

Aggregates: tasks per second, queue length per region, worker utilization,
workflow success rate. Used by GET /system/metrics and alerting.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from config.settings import REDIS_QUEUE_READY, REDIS_URL
from database.db import db
from database.workers import get_all_workers, count_active_workers
from database.regions import list_active_regions

TASKS_QUEUE_KEY = REDIS_QUEUE_READY
ACTIVE_WORKER_THRESHOLD_SEC = 30


def _get_redis_queue_length() -> int:
    """Current length of the Redis task queue."""
    try:
        import redis
        client = redis.from_url(REDIS_URL, decode_responses=True)
        return client.llen(TASKS_QUEUE_KEY)
    except Exception:
        return 0


def _parse_target_region(task_text: Any) -> Optional[str]:
    """Extract target_region from task_text JSON; returns None if missing or not JSON."""
    if task_text is None:
        return None
    s = str(task_text).strip()
    if not s or not s.startswith("{"):
        return None
    try:
        data = json.loads(s)
        r = data.get("target_region")
        return str(r).strip().lower() if r else None
    except (json.JSONDecodeError, TypeError):
        return None


def get_tasks_per_second(window_seconds: int = 60) -> float:
    """Tasks completed per second (average over the last window_seconds)."""
    try:
        cur = db.get_connection().cursor()
        cur.execute(
            """
            SELECT COUNT(*) AS n FROM tasks
            WHERE status = 'completed'
              AND completed_at >= NOW() AT TIME ZONE 'UTC' - (?::interval)
            """,
            (f"{window_seconds} seconds",),
        )
        row = cur.fetchone()
        n = row["n"] if row else 0
        return n / window_seconds if window_seconds else 0.0
    except Exception:
        return 0.0


def get_queue_length_per_region() -> Dict[str, int]:
    """
    Pending task count by target_region from the tasks table.
    Redis queue is global; this reflects DB pending tasks with target_region in task_text.
    """
    out: Dict[str, int] = {}
    try:
        cur = db.get_connection().cursor()
        cur.execute(
            "SELECT id, task_text FROM tasks WHERE status = 'pending'"
        )
        for row in cur.fetchall() or []:
            region = _parse_target_region(row.get("task_text"))
            key = region or "default"
            out[key] = out.get(key, 0) + 1
    except Exception:
        pass
    return out


def get_worker_utilization() -> Dict[str, Any]:
    """
    Worker utilization: total tasks_running, active workers, utilization ratio (0-1).
    """
    workers = get_all_workers()
    active = count_active_workers(within_seconds=ACTIVE_WORKER_THRESHOLD_SEC)
    total_running = sum(w.get("tasks_running") or 0 for w in workers)
    # Utilization = busy workers / active workers (cap at 1)
    utilization = min(1.0, total_running / active) if active else 0.0
    return {
        "tasks_running_total": total_running,
        "workers_active": active,
        "workers_registered": len(workers),
        "utilization": round(utilization, 4),
    }


def get_workflow_success_rate(window_minutes: int = 60) -> float:
    """
    Success rate (completed / (completed + failed)) for tasks in the last window.
    Uses tasks table status; no workflow_id required.
    """
    try:
        cur = db.get_connection().cursor()
        since = (datetime.utcnow() - timedelta(minutes=window_minutes))
        cur.execute(
            """
            SELECT status, COUNT(*) AS n FROM tasks
            WHERE created_at >= ? AND status IN ('completed', 'failed')
            GROUP BY status
            """,
            (since,),
        )
        rows = cur.fetchall() or []
        completed = sum(r["n"] for r in rows if r["status"] == "completed")
        failed = sum(r["n"] for r in rows if r["status"] == "failed")
        total = completed + failed
        return (completed / total) if total else 1.0
    except Exception:
        return 1.0


def get_region_metrics() -> Dict[str, Dict[str, Any]]:
    """
    Per-region metrics: queue_length (from DB pending), workers_active, tasks_running,
    tasks_completed_last_hour, tasks_failed_last_hour.
    """
    regions = list_active_regions()
    workers = get_all_workers()
    queue_by_region = get_queue_length_per_region()

    # Build worker set per region (last_seen within threshold = active)
    now = datetime.utcnow()
    try:
        now_ts = now.timestamp()
    except Exception:
        now_ts = 0

    def _seconds_ago(dt_val: Any) -> Optional[float]:
        if dt_val is None:
            return None
        try:
            if hasattr(dt_val, "timestamp"):
                return now_ts - dt_val.timestamp()
            return None
        except Exception:
            return None

    active_workers_by_region: Dict[str, List[Dict[str, Any]]] = {}
    for w in workers:
        region_id = (w.get("region") or "").strip().lower() or "default"
        last_seen = w.get("last_seen")
        if isinstance(last_seen, str):
            try:
                last_seen = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
            except Exception:
                last_seen = None
        secs = _seconds_ago(last_seen)
        is_active = secs is not None and secs <= ACTIVE_WORKER_THRESHOLD_SEC
        entry = {
            "worker_id": w.get("worker_id"),
            "tasks_running": w.get("tasks_running") or 0,
            "last_seen": w.get("last_seen"),
            "heartbeat_latency_seconds": round(secs, 2) if secs is not None else None,
            "active": is_active,
        }
        active_workers_by_region.setdefault(region_id, []).append(entry)

    # Running tasks (all) and completed/failed (last hour) by region
    running_by_region: Dict[str, int] = {}
    completed_by_region: Dict[str, int] = {}
    failed_by_region: Dict[str, int] = {}
    try:
        cur = db.get_connection().cursor()
        cur.execute(
            "SELECT id, task_text, status, created_at FROM tasks WHERE status = 'running'"
        )
        for row in cur.fetchall() or []:
            key = _parse_target_region(row.get("task_text")) or "default"
            running_by_region[key] = running_by_region.get(key, 0) + 1
        cur.execute(
            """
            SELECT task_text, status FROM tasks
            WHERE status IN ('completed', 'failed')
              AND created_at >= NOW() AT TIME ZONE 'UTC' - INTERVAL '1 hour'
            """
        )
        for row in cur.fetchall() or []:
            key = _parse_target_region(row.get("task_text")) or "default"
            if row.get("status") == "completed":
                completed_by_region[key] = completed_by_region.get(key, 0) + 1
            else:
                failed_by_region[key] = failed_by_region.get(key, 0) + 1
    except Exception:
        pass
    # Ensure all known regions have entries
    region_ids = {r["region_id"] for r in regions}
    for rid in region_ids:
        running_by_region.setdefault(rid, 0)
        completed_by_region.setdefault(rid, 0)
        failed_by_region.setdefault(rid, 0)
    running_by_region.setdefault("default", 0)
    completed_by_region.setdefault("default", 0)
    failed_by_region.setdefault("default", 0)

    result: Dict[str, Dict[str, Any]] = {}
    for r in regions:
        rid = r["region_id"]
        active_list = active_workers_by_region.get(rid, [])
        active_count = sum(1 for x in active_list if x.get("active"))
        total = completed_by_region.get(rid, 0) + failed_by_region.get(rid, 0)
        success = (completed_by_region.get(rid, 0) / total) if total else 1.0
        result[rid] = {
            "name": r.get("name", rid),
            "status": r.get("status", "active"),
            "queue_length": queue_by_region.get(rid, 0),
            "workers_active": active_count,
            "workers_registered": len(active_list),
            "tasks_running": running_by_region.get(rid, 0),
            "tasks_completed_last_hour": completed_by_region.get(rid, 0),
            "tasks_failed_last_hour": failed_by_region.get(rid, 0),
            "success_rate_last_hour": round(success, 4),
            "workers": active_list,
        }
    # Add "default" for tasks with no region
    if "default" not in result and (queue_by_region.get("default", 0) or active_workers_by_region.get("default")):
        result["default"] = {
            "name": "Default",
            "status": "active",
            "queue_length": queue_by_region.get("default", 0),
            "workers_active": sum(1 for x in active_workers_by_region.get("default", []) if x.get("active")),
            "workers_registered": len(active_workers_by_region.get("default", [])),
            "tasks_running": running_by_region.get("default", 0),
            "tasks_completed_last_hour": completed_by_region.get("default", 0),
            "tasks_failed_last_hour": failed_by_region.get("default", 0),
            "success_rate_last_hour": 1.0,
            "workers": active_workers_by_region.get("default", []),
        }
    return result


def get_worker_health() -> Dict[str, Any]:
    """
    Worker health: heartbeat latency (seconds since last_seen) per worker,
    and global task failure rate (last hour).
    """
    workers = get_all_workers()
    now = datetime.utcnow()
    try:
        now_ts = now.timestamp()
    except Exception:
        now_ts = 0
    worker_health: List[Dict[str, Any]] = []
    for w in workers:
        last_seen = w.get("last_seen")
        if isinstance(last_seen, str):
            try:
                last_seen_dt = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
                latency = round(now_ts - last_seen_dt.timestamp(), 2)
            except Exception:
                latency = None
        elif hasattr(last_seen, "timestamp"):
            latency = round(now_ts - last_seen.timestamp(), 2)
        else:
            latency = None
        worker_health.append({
            "worker_id": w.get("worker_id"),
            "region": w.get("region"),
            "tasks_running": w.get("tasks_running") or 0,
            "heartbeat_latency_seconds": latency,
            "status": w.get("status", "unknown"),
        })
    completed, failed = 0, 0
    try:
        cur = db.get_connection().cursor()
        cur.execute(
            """
            SELECT status, COUNT(*) AS n FROM tasks
            WHERE created_at >= NOW() AT TIME ZONE 'UTC' - INTERVAL '1 hour'
              AND status IN ('completed', 'failed')
            GROUP BY status
            """
        )
        for row in cur.fetchall() or []:
            if row["status"] == "completed":
                completed = row["n"]
            elif row["status"] == "failed":
                failed = row["n"]
    except Exception:
        pass
    total = completed + failed
    failure_rate = (failed / total) if total else 0.0
    return {
        "workers": worker_health,
        "task_failure_rate_last_hour": round(failure_rate, 4),
        "tasks_completed_last_hour": completed,
        "tasks_failed_last_hour": failed,
    }
