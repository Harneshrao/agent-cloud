# Agent Cloud — package layout

This directory is the **canonical modular layout** for the Agent Execution Cloud.

## Layers (dependency direction)

```
app (entrypoints)  →  core (pure domain)  ←  contracts (DTOs, events)
       ↓                        ↑
       └──────────────── infra (DB, Redis, HTTP, config)
                ↑
         execution (worker loops, promoters) — uses infra, never app
```

**Forbidden:** `infra → app`, `core → app`, `execution → app`, `infra → execution` importing app routes.

## Migration

Legacy modules (`api/`, `database/`, `workers/`, `config/`, …) remain at the repository root during migration. New code lives under `agent_cloud/`. Adapters in `infra/` may delegate to legacy packages until cutover.

## Running

```bash
# API (new factory; can mount legacy routers during migration)
uvicorn agent_cloud.app.api.main:app --reload

# Legacy (unchanged)
uvicorn api.main:app --reload
```

See repository root `ARCHITECTURE.md` for the full diagram and checklist.
