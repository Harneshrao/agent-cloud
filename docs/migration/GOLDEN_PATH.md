# Golden path — Managed Agent Hosting

Canonical ownership (single source of truth):

| Concern | Canonical location |
|---------|-------------------|
| **A. API layer** | `agent_cloud/app/api/` (mount under `/v1` today); legacy `api/` remains compatibility-only until routes are ported. |
| **B. Authentication** | `api/auth_api.py`, `api/jwt_handler.py`, `database/*session*` — port types into `agent_cloud/contracts/` then implementations into `agent_cloud/infra/` in a later slice. |
| **C. Workers** | **`workers/guaranteed_loop.py`** (loop) + **`workers/agent_executor.py`** (body); entry **`workers/canonical_worker.py`** / `app.workers.worker`. Shims: `workers/worker.py`, `execution_worker.py`. |
| **D. Scheduler** | **`workers/runtime_supervisor.py`** (Redis `scheduler_runner` + cron `scheduler_service`); entry `app.workers.scheduler` / `start_scheduler.py`. |
| **E. Queue** | `redis_queue_pkg/` + `services/task_service.py` (the `task_queue` package was removed). |
| **F. DB session** | `database/session.py` + `database/db.py` until SQLAlchemy session moves to `agent_cloud/infra/db/`. |
| **G. Deployment** | **`deploy/kubernetes/` only** (duplicate root `kubernetes/` archived). |
| **H. Dashboard** | `dashboard/app/` — allowed routes: `/login`, `/signup`, `/projects`, `/agents`, `/deployments`, `/runs`, `/logs`, `/api-keys`, `/usage`, `/system` (+ auth callback + installation configure subpaths for deploy/run). |
| **I. Billing** | `api/plans_api.py`, `api/usage_api.py`, `database/plans.py`, `database/usage_records.py`. |
| **J. Logging** | Worker structured logs + `database/task_logs` / task events as implemented in execution paths. |
| **K. Monitoring** | `api/system_api.py`, `deploy/kubernetes/monitoring/*`. |

No new parallel frameworks: extend these trees only.
