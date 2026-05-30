# Billing + Usage Economics Architecture

**Principle:** Attribution before invoicing. Abuse prevention before scale. No Stripe complexity in P0.

**Tenant boundary:** `project_id` (no separate `tenant_id` table today). Plans attach via `project_plans` → `plans`.

---

## 1. Billing architecture

### Usage model

Append-only **`usage_events`** ledger. Each billable action emits one or more events with:

| Field | Purpose |
|-------|---------|
| `project_id` | Tenant accounting |
| `event_type` | Billable category |
| `quantity` + `unit` | count, ms, bytes |
| `task_id` / `deployment_id` / `artifact_id` | Resource attribution |
| `api_key_id` | Key-level attribution (when wired) |
| `metadata` | agent name, path, error snippet |

Legacy **`usage_records`** still written on task complete for agent-cost charts.

### Pricing model (P0 = caps, not invoices)

Plans in DB (`plans`) + operational caps in `services/plan_limits.py`:

| Plan | Price | Runs/mo | Exec cap | Deployments | Storage |
|------|-------|---------|----------|-------------|---------|
| Free | $0 | 1,000 | 10 min | 5 | 100 MB |
| Starter | $29 | 10,000 | 60 min | 25 | 1 GB |
| Growth | $199 | 100,000 | 600 min | 100 | 10 GB |

### Quota model

Hard gates return **429** (`usage_quota_exceeded`) or force **DLQ** (retry storms). Soft warnings at **90%** via `get_billing_summary().warnings`.

### Tenant accounting

One project = one billing account. All workers, APIs, and storage paths are project-scoped.

### Resource attribution

```
API / enqueue → task_service → usage_events (task_enqueued)
Worker complete → usage_metering → task_completed + execution_ms
Worker fail → task_failed
Retry → task_retry (+ check_retry_allowed hourly cap)
DLQ → task_dlq
Deploy → deployment_created
Upload → artifact_uploaded (bytes)
Mutating API → api_request (middleware)
```

### Canonical enforcement points

1. **Enqueue** — `quota_service.check_enqueue_quota`
2. **Artifact upload** — `check_artifact_upload`
3. **New deployment** — `check_deployment_quota`
4. **Retry** — `check_retry_allowed` (hourly)
5. **API** — `ProjectRateLimitMiddleware` + JWT token bucket
6. **Worker** — task timeout / visibility (existing execution engine)

---

## 2. Usage attribution system

| Signal | Event | Wired |
|--------|-------|-------|
| Task executions | `task_enqueued` | `task_service` |
| Success | `task_completed` | `guaranteed_loop` |
| Failure | `task_failed` | `guaranteed_loop` |
| Retries | `task_retry` | `task_outcome` |
| DLQ | `task_dlq` | `task_outcome` |
| Execution duration | `execution_ms` | `usage_metering` |
| Deployments | `deployment_created` | `deployments_api` / pipeline |
| Artifact storage | `artifact_uploaded` | pipeline |
| API requests | `api_request` | rate-limit middleware |

**Gaps (P1):** queue wait time, worker CPU/memory, per-api-key enforcement on run endpoints, deployment storage bytes aggregate.

---

## 3. Quota system

Implementation: `services/quota_service.py` + `services/plan_limits.py`.

| Quota | Check | On exceed |
|-------|-------|-----------|
| Monthly runs | enqueue | 429 |
| Monthly execution ms | enqueue | 429 |
| Concurrent running | enqueue | 429 |
| Deployments count | deploy | 429 |
| Artifact storage | upload | 429 |
| Single upload size | upload | 429 |
| Retries/hour | retry | DLQ (no re-queue) |
| API req/min | middleware | 429 |

Fails safe: quota checks run **before** Redis enqueue / disk write.

---

## 4. Pricing model recommendation

**Recommended for PMF:** **Hybrid tier + included runs + execution-time cap.**

| Model | Pros | Cons |
|-------|------|------|
| Per-task | Simple | Punishes cheap fast agents; encourages tiny tasks |
| Compute-second | Fair | Hard to explain; variable worker cost |
| Deployment-seat | Predictable | Under-monetizes heavy runners |
| Hybrid (chosen) | Predictable spend + margin protection | Slightly more fields |

**Tiers:** Free (validate), Starter ($29, indie), Growth ($199, team).  
**Overage (P2):** soft cap + email warning, then hard block (no metered Stripe yet).

Margins protected by: concurrent caps, retry/hour caps, storage caps, execution-time caps.

---

## 5. Multi-tenant isolation

| Layer | Status |
|-------|--------|
| Project-scoped API (`X-Project-ID`) | ✅ |
| Project-scoped tasks, deployments, events | ✅ |
| API keys → project | ✅ (verify all run paths pass key id to metering) |
| Queue fairness | ⚠️ Shared Redis queues — noisy neighbor possible |
| Worker fairness | ⚠️ BRPOP global — consider per-project dequeue caps P1 |
| Quota isolation | ✅ Per-project counters |

**Recommendations:**

- P1: **weighted fair queueing** or per-project in-flight cap (already have concurrent cap)
- P1: optional **queue prefix** `queue:{project_id}` for enterprise
- P2: dedicated worker pools per plan tier

---

## 6. Rate limiting + abuse prevention

| Control | Implementation |
|---------|----------------|
| API rate limits | `ProjectRateLimitMiddleware`, JWT bucket |
| Queue flood | monthly run + concurrent caps |
| Retry storm | `max_retries_per_hour` → DLQ |
| Deployment spam | `max_deployments` |
| Oversized upload | `max_artifact_upload_mb` |
| Task timeout | worker visibility / executor timeout |

**Quota exceeded:** HTTP 429 JSON `{ detail, limit_type }`.  
**Warnings:** 90% thresholds in `/billing/summary`.  
**Temporary bans (P2):** Redis flag on repeated 429 abuse.

---

## 7. Cost analysis

| Driver | Growth pattern | Control |
|--------|----------------|---------|
| Postgres `usage_events` | Linear with actions | Monthly partition + 90d retention P1 |
| Postgres `task_events` / logs | High volume | TTL, sample debug logs |
| Redis queues | Spike under load | Depth alerts, per-project caps |
| Worker compute | ∝ execution_ms | Concurrency + time quotas |
| Artifact ZIPs | ∝ uploads | Storage quota + lifecycle P1 |
| Observability storage | Trace per task | Retention policy on `task_logs` |

**Biggest margin risk:** unbounded retries and long-running agents without execution caps.  
**Mitigation:** retry/hour cap, monthly execution ms cap, DLQ.

---

## 8. Dashboard productization

| Route | Purpose |
|-------|---------|
| `/usage` | Usage charts + billing summary metrics |
| `/limits` | Quotas vs used + warnings |
| `/deployments` | Deployment count (storage) |
| `/tasks`, `/dlq` | Failure/retry visibility |

API: `GET /billing/summary`, `/limits`, `/events`, `/usage`.

Developers see: runs, execution time, retries, DLQ, deployments, storage — not invoices.

---

## 9. Implementation plan

### P0 (done)

- [x] `usage_events` table + migration `h8i9j0k2l3`
- [x] `usage_metering` + worker/deploy/API wiring
- [x] `quota_service` gates
- [x] `/billing/*` API
- [x] Project rate limit middleware
- [x] Dashboard `/limits`, `/usage` + billing summary

### P1

- [ ] Run `alembic upgrade head` in all envs
- [ ] Wire `api_key_id` on all enqueue paths
- [ ] Queue depth enforcement (Redis LLEN check)
- [ ] `usage_events` retention job
- [ ] Assign Starter/Growth via admin API
- [ ] Per-project queue fairness

### P2

- [ ] Stripe / invoicing
- [ ] Cost forecasting from `execution_ms`
- [ ] Autoscaling-aware billing
- [ ] Overage metering

---

## Code map

| Module | Role |
|--------|------|
| `database/usage_events.py` | Ledger CRUD + aggregates |
| `services/usage_metering.py` | Event emitters |
| `services/quota_service.py` | Enforcement + summary |
| `services/plan_limits.py` | Tier caps |
| `api/billing_api.py` | HTTP surface |
| `api/middleware/project_rate_limit.py` | API flood control |
| `docs/migration/BILLING_USAGE.md` | Ops quick reference |
