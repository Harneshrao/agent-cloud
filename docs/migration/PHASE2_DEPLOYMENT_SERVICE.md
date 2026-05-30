# Phase 2 — Deployment service (MVP)

## Implemented

- `database/agent_installations.py`: `set_installation_status(installation_id, status)` for lifecycle transitions (`active`, `suspended`, `rolled_back`, `pending`).
- `agent_cloud/core/deployments/service.py`: `DeploymentApplicationService` + `DeploymentState` enum mapping to installation rows.

## Next (HTTP + pipeline)

1. `POST /v1/runtime/deployments` — upload artifact → validate → persist version metadata.
2. Worker hook — transition `pending` → `active` after health check.
3. `POST /v1/runtime/deployments/{id}:rollback` — call `transition(..., rolled_back)` + enqueue stop task.
