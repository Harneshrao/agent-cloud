# Chaos / resilience runbook

Run these in **staging** with managed Postgres + Redis (not production without approval).

## 1. Kill worker mid-task

1. Enqueue a long-running task (`EXECUTOR_MODULE` sleep stub).
2. `SIGKILL` the worker while `tasks.status = running`.
3. Wait past `VISIBILITY_TIMEOUT_SEC` + scheduler interval.
4. **Expect:** task re-queued or retried per `execution/recovery.py` + scheduler rules; no duplicate side effects if `idempotency_key` is set.

## 2. Redis restart

1. Note queue depth (`LLEN queue:ready` or project-specific key).
2. Restart Redis (or failover).
3. **Expect:** API may fail-open on rate limits; workers reconnect; tasks not lost if committed in Postgres (replay from `pending`/`queued` if needed).

## 3. Postgres restart / failover

1. Fail primary DB.
2. **Expect:** API returns 5xx until replica promoted; in-flight writes use transactions; Alembic migrations verified on cold start.

## 4. Duplicate delivery

1. Manually `LPUSH` the same `task_id` twice to the ready queue.
2. **Expect:** second execution is idempotent-safe (idempotency table + claim race).

## Automation

Automated chaos (e.g. pytest + Docker Compose) can be added under `tests/`; current repo provides manual runbook and recovery primitives.
