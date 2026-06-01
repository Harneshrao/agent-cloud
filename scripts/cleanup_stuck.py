#!/usr/bin/env python3
"""
Safe reconciliation of stuck execution state (dev/local).

Actions (none destructive to completed/failed history):
  1. Orphaned running tasks (no heartbeat within --stale-seconds) -> failed.
  2. queue:ready entries whose task is missing or already terminal  -> removed.
  3. Orphan task locks (lock:task:*) for terminal/missing tasks      -> deleted.
  4. Non-terminal tasks (queued/pending/retry) missing from queue   -> re-enqueued.

Usage:
  py -3.11 scripts/cleanup_stuck.py [--stale-seconds 120] [--dry-run]
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)
os.environ.setdefault("SKIP_MIGRATION_CHECK", "1")

from sqlalchemy import select, text, update  # noqa: E402

from config.redis_keys import REDIS_QUEUE_READY  # noqa: E402
from database.models import Task, TaskStatus  # noqa: E402
from database.session import SessionLocal  # noqa: E402

TERMINAL = {"completed", "failed", "dead"}


def _redis():
    import redis

    url = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0").replace("localhost", "127.0.0.1")
    return redis.from_url(url, socket_connect_timeout=3)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stale-seconds", type=int, default=120)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    r = _redis()
    print("redis PING:", r.ping())

    with SessionLocal() as s:
        counts = s.execute(
            text("SELECT status, count(*) FROM tasks GROUP BY status ORDER BY status")
        ).fetchall()
        print("task status (before):", {row[0]: row[1] for row in counts})

        # 1) Orphaned running -> failed
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=args.stale_seconds)
        orphaned = s.execute(
            select(Task.id).where(
                Task.status == TaskStatus.running,
                (Task.last_heartbeat.is_(None)) | (Task.last_heartbeat < cutoff),
            )
        ).scalars().all()
        print(f"orphaned running tasks: {len(orphaned)}")
        if orphaned and not args.dry_run:
            s.execute(
                update(Task)
                .where(Task.id.in_(orphaned))
                .values(status=TaskStatus.failed)
            )
            s.commit()

        # 2) + 3) Reconcile Redis queue + locks against DB
        raw_items = r.lrange(REDIS_QUEUE_READY, 0, -1)
        removed = 0
        for raw in raw_items:
            tid = raw.decode() if isinstance(raw, bytes) else str(raw)
            row = s.execute(text("SELECT status FROM tasks WHERE id = :id"), {"id": tid}).fetchone()
            if row is None or str(row[0]).lower() in TERMINAL:
                if not args.dry_run:
                    r.lrem(REDIS_QUEUE_READY, 0, raw)
                removed += 1
        print(f"stale queue:ready entries removed: {removed}")

        lock_keys = r.keys("lock:task:*")
        lock_removed = 0
        for k in lock_keys:
            ks = k.decode() if isinstance(k, bytes) else str(k)
            tid = ks.rsplit(":", 1)[-1]
            row = s.execute(text("SELECT status FROM tasks WHERE id = :id"), {"id": tid}).fetchone()
            if row is None or str(row[0]).lower() in TERMINAL:
                if not args.dry_run:
                    r.delete(k)
                lock_removed += 1
        print(f"orphan locks removed: {lock_removed}")

        # 4) Re-enqueue non-terminal tasks missing from the queue
        in_queue = {
            (raw.decode() if isinstance(raw, bytes) else str(raw))
            for raw in r.lrange(REDIS_QUEUE_READY, 0, -1)
        }
        pending = s.execute(
            select(Task.id).where(
                Task.status.in_([TaskStatus.queued, TaskStatus.pending, TaskStatus.retry])
            )
        ).scalars().all()
        requeued = 0
        for tid in pending:
            if str(tid) not in in_queue:
                if not args.dry_run:
                    r.lpush(REDIS_QUEUE_READY, str(tid))
                requeued += 1
        print(f"re-enqueued missing tasks: {requeued}")

        counts = s.execute(
            text("SELECT status, count(*) FROM tasks GROUP BY status ORDER BY status")
        ).fetchall()
        print("task status (after):", {row[0]: row[1] for row in counts})
        print("queue:ready depth:", r.llen(REDIS_QUEUE_READY), "queue:dead depth:", r.llen("queue:dead"))


if __name__ == "__main__":
    main()
