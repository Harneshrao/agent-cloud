"""
Worker autoscaling: scale workers based on queue backlog and active worker count.

Monitors queue_length (Redis), active_workers (registry), container_utilization.
Scaling rules: scale up when queue_length > active_workers * 5; scale down when
queue_length < active_workers * 2 by stopping a managed idle worker.
Runs independently of task execution, workflow controller, sandbox, and container pool.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List

from database.workers import count_active_workers

# Redis queue key; must match redis_queue_pkg / system_api
from config.settings import REDIS_QUEUE_READY as TASKS_QUEUE_KEY
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
ACTIVE_WORKER_THRESHOLD_SEC = 30

# Scaling thresholds
SCALE_UP_RATIO = 5   # scale up if queue_length > active_workers * 5
SCALE_DOWN_RATIO = 2  # scale down if queue_length < active_workers * 2
LOOP_INTERVAL_SEC = 10
MAX_ACTIONS_HISTORY = 50

_managed_processes: List[subprocess.Popen] = []
_scaling_actions: List[Dict[str, Any]] = []
_lock = threading.Lock()


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _get_queue_length() -> int:
    try:
        import redis
        client = redis.from_url(REDIS_URL, decode_responses=True)
        return client.llen(TASKS_QUEUE_KEY)
    except Exception:
        return 0


def _get_container_utilization() -> Dict[str, Any]:
    try:
        from engine.container_pool import get_pool
        pool = get_pool()
        idle = pool.idle_containers
        busy = pool.busy_containers
        total = len(idle) + len(busy)
        return {
            "containers_idle": len(idle),
            "containers_busy": len(busy),
            "containers_total": total,
            "utilization": len(busy) / total if total else 0.0,
        }
    except Exception:
        return {
            "containers_idle": 0,
            "containers_busy": 0,
            "containers_total": 0,
            "utilization": 0.0,
        }


def _record_action(action: str, detail: str = "") -> None:
    with _lock:
        _scaling_actions.append({
            "action": action,
            "detail": detail,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })
        if len(_scaling_actions) > MAX_ACTIONS_HISTORY:
            _scaling_actions.pop(0)


def start_worker() -> bool:
    """Launch a worker subprocess. Returns True if started."""
    root = _project_root()
    try:
        proc = subprocess.Popen(
            [sys.executable, "-m", "workers.worker"],
            cwd=str(root),
            env=os.environ.copy(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        with _lock:
            _managed_processes.append(proc)
        _record_action("start_worker", f"pid={proc.pid}")
        return True
    except Exception as e:
        _record_action("start_worker_failed", str(e))
        return False


def stop_idle_worker() -> bool:
    """Stop one managed worker (oldest in list that is still alive). Returns True if stopped."""
    with _lock:
        # Prune dead processes first
        alive = [p for p in _managed_processes if p.poll() is None]
        _managed_processes.clear()
        _managed_processes.extend(alive)
        if not _managed_processes:
            return False
        proc = _managed_processes.pop(0)
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
    _record_action("stop_worker", f"pid={proc.pid}")
    return True


def _run_scaling_step() -> None:
    queue_length = _get_queue_length()
    active_workers = count_active_workers(within_seconds=ACTIVE_WORKER_THRESHOLD_SEC)
    with _lock:
        managed_alive = [p for p in _managed_processes if p.poll() is None]
        managed_count = len(managed_alive)

    # Scale up: queue backlog high relative to workers
    if active_workers == 0 or queue_length > active_workers * SCALE_UP_RATIO:
        start_worker()
        return  # one action per tick

    # Scale down: queue low relative to workers; only stop workers we manage
    if managed_count > 0 and queue_length < active_workers * SCALE_DOWN_RATIO:
        stop_idle_worker()


def run_autoscaler_loop() -> None:
    """Run scaling decisions every LOOP_INTERVAL_SEC. Intended for a daemon thread."""
    while True:
        time.sleep(LOOP_INTERVAL_SEC)
        try:
            _run_scaling_step()
        except Exception:
            pass


def get_autoscaler_state() -> Dict[str, Any]:
    """Return state for GET /system/autoscaler."""
    queue_length = _get_queue_length()
    active_workers = count_active_workers(within_seconds=ACTIVE_WORKER_THRESHOLD_SEC)
    container = _get_container_utilization()
    with _lock:
        managed_alive = [p.pid for p in _managed_processes if p.poll() is None]
        actions = list(_scaling_actions)
    return {
        "active_workers": active_workers,
        "queue_length": queue_length,
        "container_utilization": container.get("utilization", 0.0),
        "containers_idle": container.get("containers_idle", 0),
        "containers_busy": container.get("containers_busy", 0),
        "managed_worker_pids": managed_alive,
        "scaling_actions": actions[-MAX_ACTIONS_HISTORY:],
    }


def start_autoscaler_background() -> None:
    """Start the autoscaler loop in a daemon thread."""
    t = threading.Thread(target=run_autoscaler_loop, daemon=True)
    t.start()
