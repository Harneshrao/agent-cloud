# Phase 10 — Migration output (incremental)

## 1. Migration report

- Machine graphs + per-file heuristic classification: `docs/migration/phase1_graphs.json`, `docs/migration/phase2_classification.json`, `docs/migration/MIGRATION_REPORT_AUTO.md`.
- Human golden path: `docs/migration/GOLDEN_PATH.md`.
- This file: executive summary.

## 2. Deleted duplication

**Removed:** `task_queue/` Python shims — imports now target `services` / `services.task_payload` / `redis_queue_pkg` (see `docs/migration/PHASE1_TASK_QUEUE_REMOVAL.md`). Duplicates remaining: legacy `api/` vs gradual extraction into `agent_cloud/core` (same ASGI app today).

## 3. Archive report

| Moved to `archive/` | From |
|---------------------|------|
| `archive/agents/competitor_intelligence` | `agents/competitor_intelligence` |
| `archive/automation_packages/competitor_research` | `automation_packages/competitor_research` |
| `archive/core_legacy/goal_mapper.py` | `core/goal_mapper.py` |
| `archive/kubernetes_root_duplicate/*` | root `kubernetes/*` |
| `archive/solana_agent` | root `solana_agent` (separate product line) |
| `archive/dashboard_legacy/*` | `dashboard/app/{war-room,marketplace,developer,automation,workflows}` |

## 4. Architecture diagram

See `docs/PRODUCTION_ARCHITECTURE.md` (text + mermaid). Wedge focus: **API → Postgres tasks → Redis queue → workers → logs/metrics**.

## 5. Production readiness checklist

- [ ] Single public API entry (`agent_cloud` cutover plan executed).
- [ ] CI: lint, typecheck, tests, OpenAPI contract diff.
- [ ] `pip-audit` / SBOM on release artifacts.
- [ ] Redis key migration (`queue:tasks` vs `queue:ready`) verified in prod.
- [ ] Worker + scheduler HA story documented.
- [ ] Secrets rotation runbook (JWT, DB, Redis).
- [ ] Dashboard auth E2E on allowed routes only.

## 6. Missing business features (for wedge)

- First-party **agent upload** UX (blob storage + validation) if not fully covered by existing install flows.
- **Structured log viewer** (not only run list) tied to `task_id` / `trace_id`.
- **Autoscale policy** UX bound to queue depth / CPU (engine exists; productize).

## 7. Next 30-day roadmap

1. Port high-traffic routes from `api/` into `agent_cloud/core` + `infra` with thin HTTP adapters (same paths preserved on the unified app).
2. ~~Replace all `from task_queue` imports~~ **Done** — delete any stale docs referencing `task_queue/*.py`.
3. Merge worker/scheduler duplicates; one Dockerfile entrypoint.
4. Expand `tests/migration/` with OpenAPI contract tests for the 10 journeys.

Run today: `python -m unittest tests.migration.test_health_contract -v` (with `SKIP_MIGRATION_CHECK=1` and valid env stubs as in the test module).
5. Remove `archive/` candidates from default Docker images after one release cycle.
