#!/usr/bin/env python3
"""
Scale agent-cloud-worker deployment by queue length and worker utilization.

Fetches GET /system/metrics (queue_length, workers_active) and sets deployment
replicas to max(MIN_REPLICAS, min(MAX_REPLICAS, ceil(queue_length / TASKS_PER_WORKER))).
Run in-cluster (as a CronJob with kubectl) or from a host with kubectl and network to platform.

Usage:
  pip install requests
  export PLATFORM_URL=http://localhost:8000
  python scale-by-queue.py [--dry-run]
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

try:
    import requests
except ImportError:
    requests = None

PLATFORM_URL = os.environ.get("PLATFORM_URL", "http://localhost:8000").rstrip("/")
MIN_REPLICAS = int(os.environ.get("MIN_REPLICAS", "2"))
MAX_REPLICAS = int(os.environ.get("MAX_REPLICAS", "20"))
TASKS_PER_WORKER = int(os.environ.get("TASKS_PER_WORKER", "5"))
DEPLOYMENT = os.environ.get("DEPLOYMENT", "agent-cloud-worker")
NAMESPACE = os.environ.get("NAMESPACE", "default")


def get_metrics() -> dict:
    if not requests:
        raise RuntimeError("pip install requests")
    r = requests.get(f"{PLATFORM_URL}/system/metrics", timeout=10)
    r.raise_for_status()
    return r.json()


def compute_replicas(metrics: dict) -> int:
    queue = int(metrics.get("queue_length", 0))
    # target = ceil(queue / TASKS_PER_WORKER), at least 1
    target = max(1, (queue + TASKS_PER_WORKER - 1) // TASKS_PER_WORKER)
    target = max(MIN_REPLICAS, min(MAX_REPLICAS, target))
    return target


def scale_deployment(replicas: int, dry_run: bool) -> None:
    cmd = ["kubectl", "scale", "deployment", DEPLOYMENT, "--replicas", str(replicas), "-n", NAMESPACE]
    if dry_run:
        print("Dry run:", " ".join(cmd))
        return
    subprocess.run(cmd, check=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="Scale worker deployment by queue length")
    ap.add_argument("--dry-run", action="store_true", help="Print scale command only")
    args = ap.parse_args()
    metrics = get_metrics()
    replicas = compute_replicas(metrics)
    print(
        f"queue_length={metrics.get('queue_length', 0)} "
        f"workers_active={metrics.get('workers_active', 0)} -> target_replicas={replicas}"
    )
    scale_deployment(replicas, args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
