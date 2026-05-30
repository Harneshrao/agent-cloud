# Incident runbook (alpha)

---

## Severity model

| Sev | Definition | Notify alpha users? |
|-----|------------|---------------------|
| **S0** | Security, data loss | Yes — pause onboarding |
| **S1** | No tasks run (worker/Redis down) | Yes — ETA |
| **S2** | High failure rate | Optional |
| **S3** | Single-tenant issue | No |

---

## Founder response checklist

1. Confirm scope: one user or all?
2. `GET /health`, `GET /observability/health` (if exposed)
3. Check worker process + Redis: `docker compose ps` / `run_all.py` logs
4. Post in alpha Slack: status + workaround
5. After fix: verify sample echo deploy + run
6. Post-mortem (3 bullets) — no blame

---

## Worker outage

**Symptoms:** Tasks stay `queued`, queue depth grows.

1. Restart worker: `py -3.11 -m workers.canonical_worker` or `run_all.py`
2. Check `REDIS_URL`
3. Logs: worker stderr for import/runtime errors

**Recovery:** Tasks should drain; no manual requeue unless documented.

---

## Redis outage

**Symptoms:** Enqueue fails, API 5xx on task routes.

1. `docker compose up -d redis` (or local Redis)
2. Verify `REDIS_URL=redis://localhost:6379/0`
3. Restart API + worker

---

## Postgres outage

**Symptoms:** 5xx on all routes, migration errors.

1. `docker compose up -d postgres`
2. `alembic upgrade head`
3. Restart API

---

## Deployment rollback (user-scoped)

User: Deployments → Rollback on previous active version.

Founder: confirm `deployment_events` show `rolled_back`.

---

## Queue recovery

If duplicate processing suspected:

1. Stop worker
2. Inspect Redis queue keys (project docs / internal tools)
3. Clear only after identifying stuck poison message
4. Restart worker

**Alpha:** prefer fixing agent and re-running over deep queue surgery.

---

## Degraded mode

| Component down | User experience | Message |
|----------------|-----------------|---------|
| API | Dashboard offline banner | ApiStatusBar |
| Worker | Tasks queue, don't complete | “Processing delayed” |
| Redis | Can't enqueue | Platform error |

---

## Emergency switches

| Env | Effect |
|-----|--------|
| `ALLOW_ANONYMOUS_DEV=0` | Require real auth (prod) |
| `ENABLE_LEGACY_PLATFORM=0` | Wedge routes only |
| Stop worker | Halts execution (maintenance) |

**Never** disable security middleware in prod.

---

## Kill switch (alpha maintenance)

1. Announce window
2. Stop worker + optionally API
3. Fix + migrate
4. Smoke test: health → sample deploy → run → trace
5. All-clear message
