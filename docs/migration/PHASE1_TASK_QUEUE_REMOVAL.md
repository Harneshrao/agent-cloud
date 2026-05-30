# Phase 1 — `task_queue` removal

## Changes

- Replaced `from task_queue.task_queue import …` with `from services.task_service import …` (and `parse_payload` from `services.task_payload`) in: `engine/`, `api/`, `database/simulation.py`, `scheduler/scheduler_service.py`, `sdk/agent.py`, `orchestrator/`.
- Replaced `from task_queue.redis_queue import push_existing_task` with `from services.task_service import push_existing_task` in `engine/dag_scheduler.py`.
- Deleted `task_queue/__init__.py`, `task_queue/task_queue.py`, `task_queue/redis_queue.py`. Left `task_queue/README.md` as pointer.

## Verification

```powershell
$env:SKIP_MIGRATION_CHECK='1'
$env:DATABASE_URL='postgresql://x:x@127.0.0.1:9/x'
python -c "from agent_cloud.app.api.main import app; print(len(app.routes))"
python -m unittest tests.migration.test_health_contract -v
```

## OpenAPI fix

- Merged duplicate `GET /system/health` handlers in `api/system_api.py` into one response; worker heartbeat detail is under `worker_health`.
