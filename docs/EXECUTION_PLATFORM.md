# Agent Execution Platform — Architecture

PostgreSQL is the **source of truth**. Redis is a **performance layer** (queues, locks, visibility timeouts, optional rate-limit cache). Workers are **stateless**: any worker can execute any task after a successful claim in Postgres.

## 1. PostgreSQL schema (authoritative)

See [`infra/postgres/execution_platform_reference.sql`](../infra/postgres/execution_platform_reference.sql) for the canonical DDL.

### Task status enum

| Value | Meaning |
|--------|---------|
| `pending` | Row created; not yet on the ready queue (or waiting schedule) |
| `queued` | Eligible on `queue:ready` (or about to be LPUSH’d) |
| `running` | Claimed by a worker (`worker_id`, `started_at` set) |
| `completed` | Success; `result` set |
| `failed` | Terminal failure before DLQ |
| `retry` | Backoff scheduled; score in `queue:retry` |
| `dead` | Exhausted retries; row in `dead_letter_queue` |
| `workflow_root` | DAG placeholder (not executed as a single worker task) |

### Invariants

- **Idempotency**: optional `idempotency_key` on `tasks` with a **partial unique index** (non-null keys only).
- **Events**: append-only `task_events` for debugging (claim, start, complete, retry, dlq).

## 2. Redis key design

**Migration note:** the canonical ready list key is `queue:ready` (see `config/redis_keys.py`). Older deployments may still have `queue:tasks`; run `RENAME queue:tasks queue:ready` in Redis once when upgrading, or drain the old list first.

| Key | Type | Purpose |
|-----|------|---------|
| `queue:ready` | LIST | Task IDs (UUID strings) ready to run — **BRPOP** |
| `queue:scheduled` | ZSET | score = run-at time **ms**; value = task_id |
| `queue:retry` | ZSET | score = next retry time **ms** |
| `queue:processing` | ZSET | score = visibility **deadline** (epoch ms); value = task_id |
| `lock:task:{task_id}` | STRING | SET NX EX — execution lease |
| `rate:{user_id}` | STRING / JSON | API rate limit (optional; API layer may use sorted sets instead) |

Namespace: set `REDIS_KEY_NAMESPACE` to prefix all keys in shared Redis.

**Redis holds no business truth** — only pointers and timers. Rebuilding queues from Postgres is possible (reconciliation job).

## 3. Task lifecycle (strict)

### API enqueue

1. `INSERT` task: `status = pending` (or `queued` if immediately runnable).
2. If `scheduled_at` in the future → `ZADD queue:scheduled` with score = ms; else `LPUSH queue:ready`.
3. `UPDATE` `status = queued` when the unit is actually on the ready path (after LPUSH or when promoted).

### Worker fetch

1. `BRPOP queue:ready` → `task_id`.

### Claim (Postgres)

```sql
UPDATE tasks
SET status = 'running',
    worker_id = :worker_id,
    started_at = now(),
    updated_at = now()
WHERE id = :task_id
  AND status IN ('queued', 'retry')
RETURNING *;
```

(Compat mode may also allow `pending` during migration.)

If **no row** → another worker won or invalid state → **skip**.

### Visibility timeout (Redis)

`ZADD queue:processing` with score = `now_ms + visibility_timeout_ms`.

### Success

1. Postgres: `status = completed`, `result = ...`, `completed_at = now()`.
2. `ZREM queue:processing` task_id.

### Failure

- If `retries < max_retries`: increment `retries`, `status = retry`, `ZADD queue:retry` with exponential backoff + jitter; remove from processing.
- Else: `status = dead`, insert `dead_letter_queue`, `ZREM` processing.

### Promoters (scheduler process)

- **Scheduled**: `ZRANGEBYSCORE queue:scheduled -inf now` → `LPUSH queue:ready`, `UPDATE status = queued`.
- **Retry**: same for `queue:retry`.
- **Stuck recovery**: `ZRANGEBYSCORE queue:processing -inf now` → treat as expired visibility → `LPUSH queue:ready`, `UPDATE status = queued` (and clear `worker_id` / `started_at` per policy).

## 4. Worker loop (conceptual)

```
task_raw = BRPOP queue:ready
task_id = parse_uuid(task_raw)

if not acquire_lock(task_id):   # SET lock:task:{id} NX EX lease
    continue

row = claim_in_postgres(task_id, worker_id)
if not row:
    release_lock(task_id)
    continue

add_to_processing(task_id, deadline_ms)

try:
    result = execute(row)
    mark_completed(task_id, result)
    remove_from_processing(task_id)
except Exception as e:
    if row.retries < row.max_retries:
        schedule_retry(task_id, backoff)
    else:
        move_to_dead_letter(task_id, e)
finally:
    release_lock(task_id)
```

Locks + conditional `UPDATE` together give **at-most-once** execution per attempt; **at-least-once** across crashes is ensured by requeue after visibility expiry.

## 5. Backoff

`delay_sec = base * (2 ** retries) + uniform(0, 3)`; store next run as `ZADD queue:retry` score = `(now + delay)_ms`.

## 6. Validation checklist

- [x] Redis contains no authoritative business state (only queue coordinates).
- [x] Postgres remains recoverable source of truth.
- [x] Workers can crash; visibility + promoter recover work.
- [x] Duplicate concurrent execution reduced by lock + claim + status filter.
- [x] Retries are deterministic given fixed backoff function and stored `retries`.

## 7. Code map

| Piece | Location |
|-------|----------|
| Redis keys | `config/redis_keys.py` |
| Queue + processing ZSET | `redis_queue_pkg/redis_queue.py` |
| Backoff | `execution/backoff.py` |
| Recovery helpers | `execution/recovery.py` |
| Scheduler loop | `workers/scheduler_runner.py` |
| Reference execution loop | `workers/execution_worker.py` |

The legacy `workers/worker.py` remains the full integration path (DAG, idempotency table, DLQ helpers). New modules document the **target** pattern and can be wired as the primary path in a follow-up.
