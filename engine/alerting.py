"""
Global observability: alert evaluation for platform operators.

Alerts for: queue backlog spikes, worker crash loops, high failure rate.
Exposed via GET /system/alerts.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List

from database.db import db
from database.workers import get_all_workers, count_active_workers
from engine.metrics_collector import (
    _get_redis_queue_length,
    get_worker_health,
    get_worker_utilization,
    ACTIVE_WORKER_THRESHOLD_SEC,
)

# Configurable thresholds (can be overridden by env)
ALERT_QUEUE_BACKLOG_THRESHOLD = int(__import__("os").environ.get("ALERT_QUEUE_BACKLOG_THRESHOLD", "500"))
ALERT_FAILURE_RATE_THRESHOLD = float(__import__("os").environ.get("ALERT_FAILURE_RATE_THRESHOLD", "0.2"))
ALERT_HEARTBEAT_STALE_SEC = int(__import__("os").environ.get("ALERT_HEARTBEAT_STALE_SEC", "120"))
# Crash loop: worker disappeared (no heartbeat) and reappeared (same worker_id or many restarts)
# We track last_seen; if a worker was active and then last_seen is very old, it may have crashed.
# "Crash loop" = multiple workers with very stale heartbeats or rapid register/drop.
ALERT_CRASH_LOOP_STALE_SEC = int(__import__("os").environ.get("ALERT_CRASH_LOOP_STALE_SEC", "90"))


def _parse_iso(last_seen: Any) -> datetime | None:
    if last_seen is None:
        return None
    if hasattr(last_seen, "timestamp"):
        return last_seen
    if isinstance(last_seen, str):
        try:
            return datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
        except Exception:
            return None
    return None


def evaluate_alerts() -> List[Dict[str, Any]]:
    """
    Evaluate all alert conditions and return a list of active alerts.
    Each alert: { "id", "severity", "message", "metric", "value", "threshold", "ts" }.
    """
    alerts: List[Dict[str, Any]] = []
    ts = datetime.utcnow().isoformat() + "Z"

    # Queue backlog spike
    queue_length = _get_redis_queue_length()
    if queue_length >= ALERT_QUEUE_BACKLOG_THRESHOLD:
        alerts.append({
            "id": "queue_backlog_spike",
            "severity": "warning",
            "message": f"Queue backlog spike: {queue_length} tasks (threshold {ALERT_QUEUE_BACKLOG_THRESHOLD})",
            "metric": "queue_length",
            "value": queue_length,
            "threshold": ALERT_QUEUE_BACKLOG_THRESHOLD,
            "ts": ts,
        })

    # High failure rate
    health = get_worker_health()
    failure_rate = health.get("task_failure_rate_last_hour", 0)
    if failure_rate >= ALERT_FAILURE_RATE_THRESHOLD:
        alerts.append({
            "id": "high_failure_rate",
            "severity": "critical",
            "message": f"High task failure rate: {failure_rate:.2%} (threshold {ALERT_FAILURE_RATE_THRESHOLD:.0%})",
            "metric": "task_failure_rate_last_hour",
            "value": failure_rate,
            "threshold": ALERT_FAILURE_RATE_THRESHOLD,
            "ts": ts,
        })

    # Worker crash loops: workers with stale heartbeats (no heartbeat for a long time)
    workers = get_all_workers()
    try:
        now_ts = datetime.utcnow().timestamp()
    except Exception:
        now_ts = 0
    stale_count = 0
    for w in workers:
        last_seen = _parse_iso(w.get("last_seen"))
        if last_seen is None:
            stale_count += 1
            continue
        try:
            age_sec = now_ts - last_seen.timestamp()
        except Exception:
            age_sec = 999999
        if age_sec > ALERT_CRASH_LOOP_STALE_SEC:
            stale_count += 1
    if stale_count > 0:
        alerts.append({
            "id": "worker_crash_loops",
            "severity": "warning",
            "message": f"{stale_count} worker(s) with heartbeat older than {ALERT_CRASH_LOOP_STALE_SEC}s (possible crash/restart)",
            "metric": "workers_stale_heartbeat",
            "value": stale_count,
            "threshold": ALERT_CRASH_LOOP_STALE_SEC,
            "ts": ts,
        })

    return alerts
