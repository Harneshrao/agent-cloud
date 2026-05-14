"""
Redis ZSET scheduler: promote due tasks from queue:scheduled and queue:retry → queue:tasks.

Run as a single replica (or leader-elected); no in-memory pools, no HTTP task delivery.
"""

from __future__ import annotations

import logging
import time

from redis_queue_pkg.redis_queue import get_task_queue

log = logging.getLogger(__name__)


def run_forever(tick_s: float = 1.0, batch: int = 500) -> None:
    q = get_task_queue()
    log.info("Redis scheduler started (ZSET → queue:tasks), tick=%ss", tick_s)
    while True:
        t0 = time.monotonic()
        now_ms = int(time.time() * 1000)
        try:
            promoted = q.promote_scheduled_and_retry(now_ms, batch=batch)
            if promoted:
                log.debug("promoted %s task(s)", len(promoted))
        except Exception:
            log.exception("promote_scheduled_and_retry failed")
        elapsed = time.monotonic() - t0
        time.sleep(max(0.0, tick_s - elapsed))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_forever()
