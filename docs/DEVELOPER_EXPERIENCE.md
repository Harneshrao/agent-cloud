# Developer experience & onboarding architecture

**Company objective:** A new developer completes deploy → run → logs → retry in **15 minutes** without founder help.

---

## 1. Developer journey (canonical)

```
Sign up (/signup)
  → Create project (/projects) + select active project
  → Upload ZIP (/deployments)
  → Deploy (automatic after upload in UI)
  → Run task (Run button or POST .../run)
  → View trace (/tasks/{id} or /runs)
  → Retry / DLQ if failed (/dlq)
  → API key for automation (/api-keys)
```

**Optimized for:** clarity, speed, confidence, low cognitive load.

---

## 2. Terminology standardization

| Use | Avoid |
|-----|--------|
| Project | Tenant, workspace (internal) |
| Deployment | Installation (marketplace), “app publish” |
| Task / run | Job (unless cron), workflow node |
| Agent | Model, AI platform |
| Artifact / version | Package (dev economy only) |
| DLQ | Dead letters (OK in nav) |
| Logs / trace | Observability (secondary) |
| Workers | Autoscaler jargon in UI |

**Removed from primary nav:** Marketplace, Agents store, System, Overview, War room, Workflows.

---

## 3. Quickstart (P0)

- **Root:** [`QUICKSTART.md`](../QUICKSTART.md) — single 15-minute path
- **Samples:** `agents/sample_echo`, `sample_fail`, `sample_slow`
- **Dashboard checklist:** Projects page `OnboardingChecklist`
- **Auth paths:** `/auth/login` and `/login` both work

---

## 4. Dashboard productization

**Primary nav (implemented):**

Projects → Deployments → Runs → Logs → DLQ → Usage → Workers

**Secondary:** API keys, Limits (footer link)

**Shell:** `ProductLayout` wraps app routes with `AuthGuard` + `AppShell`; auth pages excluded.

**Project context:** `ActiveProjectProvider` + topbar selector → automatic `X-Project-ID` on product API calls (never set headers in pages).

**Frontend state (canonical):** See [`FRONTEND_STATE_ARCHITECTURE.md`](FRONTEND_STATE_ARCHITECTURE.md) — project lifecycle, onboarding engine, API connectivity, unified `PlatformAlert` / `PageState`.

**PMF & activation analytics:** See [`PMF_ANALYTICS.md`](PMF_ANALYTICS.md) — `product_events`, funnel, founder dashboard at `/founder`.

**Private alpha:** See [`ALPHA_PRIVATE.md`](ALPHA_PRIVATE.md) and [`runbooks/`](runbooks/) — readiness, support, incidents, interviews.

---

## 5. OpenAPI + API DX

**Wedge surface (always on):**

- `/auth/*`, `/login`, `/register`, `/projects`
- `/deployments/*`
- `/observability/*`
- `/billing/*`
- `/api-keys`
- `/agents/v2/run` (optional programmatic)
- `/health`

**Hidden unless `ENABLE_LEGACY_PLATFORM=1`:** marketplace, workflows, war room, templates, simulation, autonomous, in-memory agents registry.

OpenAPI description on `FastAPI` documents the deployment-first flow.

**Errors:** Structured `detail` with `error`, `message`, `hint` via `api/api_errors.py`.

---

## 6. Error experience

| Failure | `error` code | Hint |
|---------|--------------|------|
| Bad ZIP | `upload_failed` | agent.yaml + agent.py, 10 MB |
| Quota | `usage_quota_exceeded` | /billing/limits |
| Deploy | `deployment_failed` | Re-upload, fix manifest |
| Auth | `auth_failed` | Bearer token or API key |

Dashboard: `lib/errors.ts` → `parseApiError()` for object details.

---

## 7. Sample projects

| Agent | Purpose |
|-------|---------|
| `sample_echo` | Happy path echo |
| `sample_fail` | Retry / recovery |
| `sample_slow` | Duration / timeout teaching |

All use sync `class Agent: def run(self, state)` for deployment runtime compatibility.

---

## 8. PMF friction analysis

| Friction | Severity | Fix (P0) |
|----------|----------|----------|
| No shell / auth on pages | Critical | ProductLayout + AuthGuard |
| Auth path `/auth/login` vs `/login` | High | Dual-mount auth router |
| Static project id `"1"` | High | Project picker + localStorage |
| Marketplace nav confusion | High | Removed from nav; /agents redirects |
| Split docs | High | QUICKSTART.md |
| async sample agent | High | Sync sample_echo |
| Opaque API errors | Medium | api_errors + parseApiError |
| OpenAPI noise | Medium | ENABLE_LEGACY_PLATFORM gate |
| No in-app tour | Low (P2) | Checklist on projects |

**Highest leverage:** one quickstart doc + working dashboard shell + project selector + deployment page.

---

## 9. Implementation plan

### P0 — done

- [x] QUICKSTART.md
- [x] Dashboard shell + simplified nav
- [x] `ActiveProjectProvider` + auto-select project + top bar
- [x] `ProjectGate` + friendly errors (no raw X-Project-ID)
- [x] `FirstSuccessBanner` + onboarding progress (localStorage)
- [x] `EmptyState` on deployments, runs, logs, DLQ, workers, API keys
- [x] One-click `POST /deployments/onboarding/sample/{name}`
- [x] API keys: create + copy + curl example
- [x] Task trace failure guidance
- [x] Sample agents (echo, fail, slow)
- [x] Structured API errors (deployments)
- [x] Legacy API feature flag
- [x] Auth `/auth` prefix
- [x] Agents page → deployments redirect
- [x] Fixed deployment API calls to use `fetchProductApi` (project header)

### P1

- [ ] Post-run deep link to task trace from Deployments
- [ ] `ac` CLI (`deploy`, `run`, `logs`)
- [ ] Onboarding analytics events
- [ ] Refresh token implementation or remove UI paths

### P2

- [ ] Guided onboarding wizard
- [ ] One-click sample deploy from UI
- [ ] OpenAPI export filtered to wedge tags only
