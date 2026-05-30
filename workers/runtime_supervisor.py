"""
Unified scheduler process: Redis queue promoter + cron enqueue loop.

Run:
  python -m workers.runtime_supervisor
  python start_scheduler.py

Both must run in every environment (local, Docker, Kubernetes) so retries,
delayed tasks, and visibility recovery work alongside cron-based schedules.
"""

from __future__ import annotations

import os
import threading


def _redis_promoter_loop() -> None:
    from workers.scheduler_runner import main

    main()


def _cron_enqueue_loop() -> None:
    tick = int(os.environ.get("CRON_SCHEDULER_TICK_SEC", "30"))
    from scheduler.scheduler_service import run_loop

    run_loop(tick_interval=tick)


def main() -> None:
    redis_thread = threading.Thread(
        target=_redis_promoter_loop,
        name="redis-scheduler-runner",
        daemon=True,
    )
    redis_thread.start()
    print(
        "runtime_supervisor: redis promoter (scheduler_runner) + cron enqueue "
        f"(tick={os.environ.get('CRON_SCHEDULER_TICK_SEC', '30')}s)"
    )
    try:
        _cron_enqueue_loop()
    except KeyboardInterrupt:
        print("runtime_supervisor: shutting down")


if __name__ == "__main__":
    main()
