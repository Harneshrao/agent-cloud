"""
Process-local metrics (counters/gauges). For production, expose via Prometheus:

    pip install prometheus_client
    from prometheus_client import Counter, Histogram
    # replace Metrics.inc_* with Counter(...)
"""

from __future__ import annotations

import threading
from typing import Any

_lock = threading.Lock()
_counts: dict[str, float] = {}
_gauges: dict[str, float] = {}


class Metrics:
    """Thread-safe counters for tasks/sec, failures, retries (export to Prometheus in prod)."""

    @staticmethod
    def inc(name: str, value: float = 1.0) -> None:
        with _lock:
            _counts[name] = _counts.get(name, 0.0) + value

    @staticmethod
    def set_gauge(name: str, value: float) -> None:
        with _lock:
            _gauges[name] = value

    @staticmethod
    def snapshot() -> dict[str, Any]:
        with _lock:
            return {"counters": dict(_counts), "gauges": dict(_gauges)}

    # Canonical names
    TASK_CLAIMED = "task_claimed_total"
    TASK_COMPLETED = "task_completed_total"
    TASK_FAILED = "task_failed_total"
    TASK_RETRY = "task_retry_total"
    QUEUE_LATENCY_MS = "queue_latency_ms"
    WORKER_HEARTBEAT = "worker_heartbeat_total"
