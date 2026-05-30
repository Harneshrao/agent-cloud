# Deployment pipeline — wedge product path

## Architecture

| Concept | Storage | Notes |
|---------|---------|--------|
| **Artifact** | `agent_artifacts` + `storage/projects/{pid}/artifacts/{aid}/package.zip` | Validated ZIP + manifest |
| **Deployment** | `agent_deployments` | Binds project → artifact version |
| **Events** | `deployment_events` | Observable state transitions |
| **Execution** | Task payload `deployment_id` + `runtime=deployment` | Worker loads ZIP via `deployment_runtime` |

## State machines

**Artifact:** `uploaded` → `validating` → `validated` | `failed`

**Deployment:** `uploaded` → `validating` → `validated` → `building` → `ready` → `deploying` → `active` | `failed` | `rolled_back` | `archived`

## HTTP API (project header required)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/deployments/artifacts/upload` | ZIP upload + validate |
| GET | `/deployments/artifacts` | List versions |
| POST | `/deployments` | Deploy artifact (`artifact_id`) |
| GET | `/deployments` | List deployments |
| POST | `/deployments/{id}/run` | Enqueue task |
| POST | `/deployments/{id}/rollback` | Rollback to previous |
| GET | `/deployments/{id}/health` | Health + checksum |
| GET | `/deployments/{id}/events` | Lifecycle events |

## 15-minute quickstart

```bash
# 1. Zip sample agent
cd agents/sample_echo && zip -r ../../sample_echo.zip agent.yaml agent.py && cd ../..

# 2. Upload (replace PROJECT_UUID and TOKEN)
curl -X POST http://localhost:8000/deployments/artifacts/upload \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Project-ID: $PROJECT_UUID" \
  -F "file=@sample_echo.zip"

# 3. Deploy (use artifact_id from response)
curl -X POST http://localhost:8000/deployments \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Project-ID: $PROJECT_UUID" \
  -H "Content-Type: application/json" \
  -d '{"artifact_id":"<ARTIFACT_UUID>"}'

# 4. Run
curl -X POST http://localhost:8000/deployments/<DEPLOYMENT_UUID>/run \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Project-ID: $PROJECT_UUID" \
  -H "Content-Type: application/json" \
  -d '{"input":{"message":"hello"}}'
```

## Code map

- `api/deployments_api.py` — HTTP
- `agent_cloud/core/deployments/pipeline.py` — upload/deploy/rollback
- `database/deployment_store.py` — persistence
- `agent_runtime/deployment_storage.py` — local files
- `agent_runtime/deployment_runtime.py` — worker execution
