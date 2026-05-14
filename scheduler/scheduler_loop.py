"""
Promote due delayed/retry tasks from Redis ZSETs to the ready LIST.

Run as a single process (or leader-elected) alongside workers.
"""

from __future__ import annotations

import time

from scheduler.redis_scheduler import run_forever as run_scheduler_loop


if __name__ == "__main__":
    print("Scheduler (Redis ZSET → queue:tasks); tick=1s. Ctrl+C to stop.")
    run_scheduler_loop()
