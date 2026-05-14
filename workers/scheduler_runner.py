"""
Promote scheduled + retry ZSETs into queue:ready; recover stale visibility timeouts.

Run as a separate process alongside stateless execution workers:
  python -m workers.scheduler_runner
"""

from __future__ import annotations

import os
import time

from execution.recovery import requeue_stale_visibility_tasks
from redis_queue_pkg.redis_queue import get_task_queue


def main() -> None:
    interval = float(os.environ.get("SCHEDULER_TICK_SEC", "1"))
    print("scheduler_runner: tick every", interval, "s")
    q = get_task_queue()
    while True:
        now_ms = int(time.time() * 1000)
        try:
            q.promote_scheduled_and_retry(now_ms, batch=500)
        except Exception as e:
            print("promote error:", e)
        try:
            n = requeue_stale_visibility_tasks(batch=200)
            if n:
                print("recovered visibility:", len(n), "tasks")
        except Exception as e:
            print("recovery error:", e)
        time.sleep(interval)


if __name__ == "__main__":
    main()
