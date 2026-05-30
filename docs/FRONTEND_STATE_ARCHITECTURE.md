# Frontend state architecture

Agent Cloud dashboard state is split by concern so pages never leak backend assumptions (headers, raw errors, undefined globals).

---

## 1. Canonical sources

| Concern | Owner | Persistence |
|--------|--------|-------------|
| Active project | `context/active-project.tsx` + `lib/project.ts` | `localStorage` key `agent_cloud_project_id` |
| API connectivity | `context/platform-state.tsx` | In-memory poll (`/health`) |
| Onboarding progress | `lib/onboarding.ts` + `hooks/use-onboarding-progress.ts` | `localStorage` + `agentcloud:onboarding-changed` event |
| API errors (copy) | `lib/platform-errors.ts` → `PlatformAlert` | Derived from thrown messages |
| Product HTTP | `lib/api.ts` `fetchProductApi` | Injects `X-Project-ID` from `getActiveProjectId()` |

**Deprecated:** `NEXT_PUBLIC_PROJECT_ID` — do not rely on env for project context; use the topbar selector.

---

## 2. Lifecycles

### Active project

1. Hydrate `projectId` from `localStorage` on mount (no flash).
2. `refreshProjects()` loads `/projects`, validates stored id, auto-selects if exactly one project.
3. Invalid stored id is cleared; first project selected when available.
4. `setProject(id)` updates storage + onboarding step `project`.
5. `ProjectGate` blocks product routes until `hasProject`; shows `PlatformAlert` if project list failed while offline.

### Onboarding (first success loop)

Steps: `project` → `deployed` → `ran` → `viewed_logs` → `api_key`.

- Marked only on **user actions** (deploy sample, upload, run task, open trace, create API key, select project).
- **Not** marked by merely loading lists with existing data.
- `markOnboardingStep` dispatches `ONBOARDING_CHANGED_EVENT`; `FirstSuccessBanner` subscribes via `useOnboardingProgress`.

### API connectivity

- `PlatformStateProvider` polls `/health` every 30s when up, 3s when down.
- `ApiStatusBar` shows a non-blocking strip when offline (degraded mode, not a full-screen blocker).

### Loading / error / empty

- `PageLoader` / `PageState` / `PlatformAlert` in `components/product/`.
- Errors classified: `offline`, `auth`, `quota`, `project`, `validation`, `server`, `unknown`.
- Each view includes title, message, hint, fault (`user` | `platform`), `retryable`.

---

## 3. HTTP rules

- **Platform routes** (`/projects`, auth): `fetchApi` / `authHeaders` — no project header required.
- **Product routes** (deployments, observability, keys): `fetchProductApi` — asserts project + `projectHeaders()`.
- **SWR** default fetcher: `apiFetch` (includes project header when set).

Never reference `PROJECT_ID` or manual headers in pages.

---

## 4. Implementation priority

### P0 (done / in progress)

- Fix `projectHeaders()` → `getActiveProjectId()`
- `PlatformStateProvider` + `ApiStatusBar`
- `PlatformAlert` + `toPlatformError`
- Onboarding events + reactive banner
- Remove env project fallback; clear invalid stored ids
- Onboarding marks tied to actions only

### P1

- Optimistic deploy/run UI
- Server-derived onboarding sync (deployments count, keys exist)
- Shared `useAsyncPage` hook across all product pages

### P2

- SWR stale-while-revalidate per resource
- Realtime onboarding / deployment sync

---

## 5. Trust-breaking issues (ranked)

| Rank | Issue | Fix |
|------|--------|-----|
| 1 | `PROJECT_ID is not defined` | `projectHeaders()` uses `getActiveProjectId()` |
| 2 | Stale `NEXT_PUBLIC_PROJECT_ID=1` | Removed client env fallback |
| 3 | Raw "API not reachable" blocks | `PlatformAlert` + `ApiStatusBar` |
| 4 | Onboarding marks on list load | Action-only marks + event bus |
| 5 | Banner not updating | `useOnboardingProgress` |
| 6 | Inconsistent error UI | `PlatformAlert` rollout |

---

## 6. File map

```
dashboard/
  context/active-project.tsx
  context/platform-state.tsx
  lib/project.ts
  lib/onboarding.ts
  lib/platform-errors.ts
  lib/api.ts
  hooks/use-onboarding-progress.ts
  components/product/platform-alert.tsx
  components/product/page-state.tsx
  components/product/api-status-bar.tsx
  components/product/project-gate.tsx
  components/product/first-success-banner.tsx
  app/providers.tsx
```
