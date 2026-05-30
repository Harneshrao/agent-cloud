# Canonical execution architecture

**Status:** Implemented (BUILD MODE — execution stabilization).

## Decision

| Role | Canonical module | Notes |
|------|------------------|--------|
| **Worker loop** | `workers/guaranteed_loop.py` | BRPOP → lock → claim → visibility ZSET → idempotency → execute → events/metrics |
| **Execution body** | `workers/agent_executor.py` | v2, pipeline, DAG; no status side effects |
| **Retry / DLQ** | `workers/task_outcome.py` | ZSET `queue:retry` + backoff; Postgres `dead_letter_tasks` |
| **Worker entry** | `workers/canonical_worker.py` | `python -m workers.canonical_worker` or `app.workers.worker` |
| **Redis scheduler** | `workers/scheduler_runner.py` | Promote scheduled/retry; visibility recovery via `execution/recovery.py` |
| **Cron scheduler** | `scheduler/scheduler_service.py` | Cron / agent_schedules → `enqueue_task` |
| **Unified scheduler process** | `workers/runtime_supervisor.py` | Both loops in one OS process |
| **Enqueue** | `services/task_service.py` | Unchanged |

## Compatibility shims (do not extend)

| Path | Behavior |
|------|----------|
| `workers/worker.py` | Calls `canonical_worker.main()` |
| `workers/execution_worker.py` | Deprecated → `canonical_worker` |
| `agent_cloud/execution/worker/loop.py` | Delegates to `canonical_worker` |
| `services.task_service.fetch_next_task` | Legacy claim-before-lock; **not** used by canonical loop |

## Environment parity

| Environment | Worker | Scheduler |
|-------------|--------|-----------|
| `run_all.py` | `-m workers.canonical_worker` | `-m workers.runtime_supervisor` |
| Docker worker | `app.workers.worker` | `app.workers.scheduler` |
| Docker scheduler image | — | `app.workers.scheduler` → supervisor |
| K8s | Same images | Same |

## Required env

- `WORKER_ID` — optional; auto-generated if unset
- `VISIBILITY_TIMEOUT_SEC` — default 300
- `SCHEDULER_TICK_SEC` — Redis promoter interval (default 1)
- `CRON_SCHEDULER_TICK_SEC` — cron enqueue interval (default 30)
- `EXECUTOR_MODULE` / `EXECUTOR_CALLABLE` — override executor (default `workers.agent_executor.run`)

## Rollback

Set `EXECUTOR_MODULE` to a custom module, or temporarily restore pre-migration `workers/worker.py` from git. Scheduler: run `scheduler_runner` and `start_scheduler` as separate processes if supervisor threading is suspect.
