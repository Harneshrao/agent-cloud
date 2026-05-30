# Agent Cloud — 15-minute quickstart

Get from zero to **deploy → run → logs → retry** without talking to anyone.

## What you are building

Agent Cloud runs **your Python agent** from a ZIP (`agent.yaml` + `agent.py`) inside a **project**. You **deploy** a version, **run** tasks, and read **logs** and the **DLQ** when things fail.

| Term | Meaning |
|------|---------|
| **Project** | Your tenant workspace (billing, quotas, isolation) |
| **Artifact** | Uploaded ZIP (validated) |
| **Deployment** | Active version of an agent in a project |
| **Task / run** | One execution enqueued to workers |
| **DLQ** | Tasks that failed after max retries |

## 1. Start the stack (3 min)

```powershell
cd c:\Users\harne\agent-cloud
py -3.11 -m pip install -r requirements.txt
alembic upgrade head
py -3.11 run_all.py
```

In another terminal:

```powershell
cd dashboard
npm install
npm run dev
```

Open http://localhost:3000 — API docs: http://localhost:8000/docs

**Dashboard env** (`dashboard/.env.local`):

```
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

Use the **API port (8000)**, not the dashboard port (3000). If the API binds to 8001, match that URL.

**Local dev:** `ALLOW_ANONYMOUS_DEV=1` in `run_all.py` skips login. For a realistic path, register at `/signup` and sign in.

**Private alpha ops:** [`docs/ALPHA_PRIVATE.md`](docs/ALPHA_PRIVATE.md)

## 2. Create a project (1 min)

**Dashboard:** Projects → Create → **Use project**

**API:**

```bash
curl -X POST http://localhost:8000/projects \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"my-first-project"}'
```

Save `project.id` as `PROJECT_ID`.

## 3. Package the sample agent (1 min)

```powershell
cd agents\sample_echo
Compress-Archive -Path agent.yaml,agent.py -DestinationPath ..\..\sample_echo.zip -Force
cd ..\..
```

Or on macOS/Linux:

```bash
cd agents/sample_echo && zip -r ../../sample_echo.zip agent.yaml agent.py && cd ../..
```

## 4. Upload & deploy (3 min)

```bash
export TOKEN="..."          # from POST /auth/login or /login
export PROJECT_ID="..."     # UUID from step 2

curl -X POST http://localhost:8000/deployments/artifacts/upload \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Project-ID: $PROJECT_ID" \
  -F "file=@sample_echo.zip"
```

Copy `artifact.artifact_id`, then:

```bash
curl -X POST http://localhost:8000/deployments \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Project-ID: $PROJECT_ID" \
  -H "Content-Type: application/json" \
  -d "{\"artifact_id\":\"<ARTIFACT_ID>\"}"
```

Copy `deployment.deployment_id`.

**Dashboard:** Deployments → Upload agent ZIP (same flow, one click).

## 5. Run a task (2 min)

```bash
curl -X POST "http://localhost:8000/deployments/<DEPLOYMENT_ID>/run" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Project-ID: $PROJECT_ID" \
  -H "Content-Type: application/json" \
  -d '{"input":{"message":"hello from curl"}}'
```

Response includes `task_id`.

## 6. See logs & status (3 min)

```bash
curl "http://localhost:8000/observability/tasks/<TASK_ID>" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Project-ID: $PROJECT_ID"
```

**Dashboard:** Runs → open task → trace + logs. Or **Logs** for recent activity.

## 7. API key (2 min)

Dashboard → API keys → create key (`ak_live_...`).

Use the same header as JWT:

```bash
curl -H "Authorization: Bearer ak_live_..." -H "X-Project-ID: $PROJECT_ID" ...
```

## Teaching examples

| Sample | Path | Teaches |
|--------|------|---------|
| Echo | `agents/sample_echo` | Happy path |
| Fail | `agents/sample_fail` | Retries → recovery |
| Slow | `agents/sample_slow` | Execution time / timeout |

## Common errors

| Message | What to do |
|---------|------------|
| `usage_quota_exceeded` | Check `/billing/limits` or wait for monthly reset |
| `Package must contain agent.yaml` | Zip must include both files |
| `Select a project first` | Set active project in dashboard or `X-Project-ID` |
| `Deployment is not active` | Re-deploy or check status on Deployments page |
| `API not reachable` | Run `py -3.11 run_all.py` |

## Next

- [`docs/DEVELOPER_EXPERIENCE.md`](docs/DEVELOPER_EXPERIENCE.md) — full DX architecture
- [`docs/migration/DEPLOYMENT_PIPELINE.md`](docs/migration/DEPLOYMENT_PIPELINE.md) — deployment details
- [`SETUP.md`](SETUP.md) — environment setup

Legacy marketplace/workflow APIs are hidden unless `ENABLE_LEGACY_PLATFORM=1`.
