# Security + Production Hardening Architecture

**Principle:** Untrusted agent code must not crash the platform, escape isolation, exhaust shared resources, or access another project.

**Trust boundary:** `project_id` + authenticated principal (JWT or `ak_live_*` API key).

---

## 1. Security architecture

### Trust boundaries

```
Internet → API (auth + project + quota + rate limit)
         → Postgres (project-scoped rows)
         → Redis queues (shared; fairness via quotas)
         → Workers (untrusted code execution zone)
         → Artifact storage (project paths only)
```

### Canonical models

| Layer | Model |
|-------|--------|
| **Auth** | JWT (users) or `Bearer ak_live_*` (API keys, hashed at rest) |
| **Authorization** | `require_project_context` + role (`owner`/`member`/`viewer`) |
| **Secrets** | Env for platform; deployment `configuration` JSONB — redacted in API, full only in worker |
| **Execution isolation** | Docker (`USE_DOCKER_RUNTIME=1`) recommended prod; in-process + 60s thread timeout dev |
| **Upload trust** | Validate zip → safe extract → manifest allowlist (`python` only) |

### Isolation boundaries

- **Project:** all tasks, deployments, billing, observability scoped by `X-Project-ID`
- **Deployment:** `execute_deployment_task` verifies `project_id` match
- **Worker:** one task per lock; visibility timeout + DLQ on failure
- **Admin:** `/system/*` requires `is_admin`

---

## 2. Runtime sandboxing

| Threat | Control |
|--------|---------|
| Arbitrary Python | Docker: `--network none`, memory/CPU/pids, read-only root |
| Infinite loop | `AGENT_TIMEOUT_SECONDS` (default 60) via `run_with_timeout` |
| Memory exhaustion | Thread timeout + `MemoryLimitExceededError`; Docker mem cap |
| Subprocess in agent | Not blocked in-process — **use Docker in prod** |
| Network from agent | Docker `--network none`; tools use SSRF guard |
| pip install | Requirement line validation; run in isolated env (P1: Docker build stage) |

**Production env:**

```bash
ENVIRONMENT=production
REQUIRE_DOCKER_FOR_DEPLOYMENTS=1
USE_DOCKER_RUNTIME=1
AGENT_TIMEOUT_SECONDS=60
```

---

## 3. Upload security

| Control | Implementation |
|---------|----------------|
| Zip-slip | `validate_agent_zip` + `safe_extract_zip` (all extract paths) |
| Size | 10 MB validator; `MAX_ARTIFACT_BYTES`; body limit middleware |
| File count | Max 100 files |
| Manifest | `agent.yaml` required; runtime ∈ `{python}` |
| Checksum | SHA-256 on upload (`deployment_storage`) |
| Path escape on read | `resolve_artifact_path` must stay under storage root |

**P1:** quarantine bucket, static scan of `agent.py`, signed artifacts.

---

## 4. Auth + authorization audit

| Area | Status |
|------|--------|
| JWT | HS256; weak default blocked in prod (`production_guard`) |
| API keys | Wired in `get_current_user` (`ak_live_*`) |
| Project APIs | `require_project_context` |
| Run/upload | `require_project_can_run` |
| Deployments | Project-scoped + quota |
| Observability | Project-scoped (`/observability/*`) |
| System | `require_admin` |
| Webhooks | HMAC + **required `X-Project-ID`** + enqueue quota |
| Legacy `/agent/run` | Fixed — requires project context (per red-team follow-up) |

**Dev-only (never prod):** `ALLOW_ANONYMOUS_DEV=1`

---

## 5. Failure containment

| Failure | Containment |
|---------|-------------|
| Worker crash | Visibility timeout → `requeue_stale_visibility_tasks` |
| Poison task | Max retries → DLQ (`task_outcome`) |
| Retry storm | Hourly retry cap → DLQ |
| Deployment crash | Task fails; deployment stays active; rollback API |
| Executor exception | Circuit breaker in `guaranteed_loop` |
| Platform overload | Quotas + rate limits + `DISABLE_TASK_ENQUEUE` kill switch |

Tasks fail **closed** (DLQ) rather than infinite retry.

---

## 6. Incident recovery model

| Severity | Example | Response |
|----------|---------|----------|
| SEV1 | Queue flood / auth bypass | `DISABLE_TASK_ENQUEUE=1`; scale workers to 0 |
| SEV2 | Retry storm | Lower `max_retries_per_hour`; inspect DLQ |
| SEV3 | Bad deployment | Rollback deployment; disable artifact |
| SEV4 | Worker stuck | Run visibility recovery / restart workers |

**Runbook commands:**

```bash
# Stop new work
export DISABLE_TASK_ENQUEUE=1

# Recovery (scheduler)
python -m workers.scheduler_runner   # promotes retries + stale visibility

# Rollback
POST /deployments/{id}/rollback  # with project auth
```

**Degraded mode:** API stays up; enqueue rejected; workers drain queue.

---

## 7. Secrets + configuration

| Secret type | Storage | Exposure |
|-------------|---------|----------|
| `JWT_SECRET` | Env | Never in responses |
| `WEBHOOK_SECRET*` | Env | HMAC only |
| DB URL | Env | Server only |
| Deployment config | JSONB | API redacted (`security/secrets.py`); worker full |
| API keys | SHA-256 hash | Plain shown once at create |

**Rotation:** rotate JWT secret (invalidates sessions); rotate webhook secrets per source; re-deploy with new config keys.

---

## 8. Scaling + abuse analysis

| Attack | Mitigation |
|--------|------------|
| Task spam | Monthly run + concurrent quotas |
| Retry storm | Hourly retry cap |
| Deploy spam | `max_deployments` |
| Storage fill | Artifact storage quota |
| API abuse | Project + user rate limits |
| Log flood | Body size limits; P1 log sampling |
| Webhook flood | HMAC + project scope + quota |

**P2:** temporary ban flag in Redis per project.

---

## 9. Implementation plan

### P0 (implemented)

- [x] `safe_extract_zip` — all deployment/manifest/package extract paths
- [x] `resolve_artifact_path` — storage root enforcement
- [x] `production_guard` — prod JWT/anon/docker checks
- [x] API key auth in `get_current_user`
- [x] Deployment secrets redacted in API
- [x] Docker path for deployments when `USE_DOCKER_RUNTIME=1`
- [x] Webhook project scoping + quota
- [x] Tool SSRF via `security/ssrf.py`, no redirects
- [x] `DISABLE_TASK_ENQUEUE` emergency switch
- [x] Deployment execution double-timeout (executor + worker)

### P1

- [ ] Default Docker in prod compose/K8s
- [ ] pip install inside container image build
- [ ] Visibility lease renewal for long tasks
- [ ] Rate limit fail-closed when Redis down
- [ ] Queue depth gate before enqueue

### P2

- [ ] gVisor/Firecracker
- [ ] Dependency scanning (OSV)
- [ ] Runtime policy engine (OPA)

---

## Code map

| Module | Role |
|--------|------|
| `agent_runtime/safe_extract.py` | Safe unzip |
| `config/production_guard.py` | Startup + kill switches |
| `security/secrets.py` | Config redaction |
| `security/ssrf.py` | Outbound URL policy |
| `agent_runtime/deployment_runtime.py` | Scoped execution + Docker |
| `agent_runtime/docker_executor.py` | Container isolation |
| `api/auth_api.py` | JWT + API keys |
| `api/webhook_api.py` | HMAC + project + quota |

See also: `SECURITY_RED_TEAM_REPORT.md` (historical findings), `docs/migration/BILLING_USAGE.md` (economic abuse controls).
