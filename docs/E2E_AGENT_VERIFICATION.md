# End-to-end: API → Redis → Worker → Postgres

## Prerequisites

- `docker compose up -d` (postgres, redis, api, worker, scheduler) with **images built from this repo** (includes `discover_agents()` on API startup and in the worker).
- `ALLOW_ANONYMOUS_DEV=1` for local calls without JWT (default in Compose).
- `X-Project-ID` must be a UUID; default project UUID from config works with anonymous dev (`00000000-0000-4000-8000-000000000002`).

## Agent name

`/agents/v2/run` resolves agents via `agent_runtime.loader` (`agents/*/agent.py`, `AgentBase`).

- **`market_research.research_agent`** (from external docs) is **not** registered by the filesystem loader (`get_agent_class` → `None`) → API returns **400 Unknown v2 agent**.
- Use a registered agent: add `agents/<your_agent>/agent.py` exporting a subclass of `AgentBase` (see `agent_runtime.loader`). The old **`Competitor Intelligence Agent`** lived under `archive/agents/competitor_intelligence/` and is no longer discovered by default.

## 1. Submit task (PowerShell)

```powershell
$headers = @{
  "Content-Type"  = "application/json"
  "X-Project-ID"  = "00000000-0000-4000-8000-000000000002"
}
$body = @{
  agent_name = "<YourAgentNameFromAgentClass>"
  task_text  = "E2E verify"
  input      = @{ urls = @("https://example.com") }
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Uri "http://localhost:8000/agents/v2/run" -Method POST -Headers $headers -Body $body
```

Expect JSON with **`task_id`** (UUID) and **`status`: `task queued`**.

## 2. API logs (startup)

After migrations, logs should include:

`PostgreSQL OK: DATABASE_URL loaded from environment; migration check passed.`

## 3. Worker logs

```bash
docker logs agent-cloud-worker-1 2>&1 | tail -n 80
```

Expect processing lines for the task (runtime `v2` path uses `execute_agent_task`).

## 4. Database

```bash
docker exec -it agent-cloud-postgres-1 psql -U agent -d agent_cloud -c "SELECT id, status, output_json IS NOT NULL AS has_output FROM tasks ORDER BY created_at DESC LIMIT 3;"
```

Expect latest task **`status`** → **`completed`** (or **`failed`** if agent/worker error).

## 5. Redis queue (optional)

```bash
docker exec agent-cloud-redis-1 redis-cli LLEN queue:ready
```

Should be **0** after the worker drains the queue (may spike briefly).

## Troubleshooting

| Symptom | Check |
|--------|--------|
| **404** on `/agents/v2/run` | API image is stale; rebuild `api` from current `api/main.py` (includes `agents_v2` router). |
| **400 Unknown v2 agent** | Agent not in registry; run `discover_agents()` (API + worker) and use a valid `agent_name`. |
| Worker never runs v2 | Worker must call `discover_agents()` before `execute_agent_task` (patched in `workers/worker.py`). |
