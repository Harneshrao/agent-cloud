# Phase 10 — Launch pack

## 1. Production readiness score

**6.5 / 10** — Single ASGI graph, `task_queue` removed, OpenAPI duplicate fixed, contract tests green. Remaining: full deployment pipeline automation, 80% coverage, prod-only secrets, horizontal worker SLO proof.

## 2. Security checklist

- [ ] JWT secret rotation + key versioning
- [ ] Postgres TLS + least-privilege DB role
- [ ] Redis AUTH + TLS in cloud
- [ ] Admin routes (`/system/*`) behind authZ + network policy
- [ ] `pip-audit` / image scan in CI
- [ ] Rate limits enabled (`ENABLE_TOKEN_BUCKET` where applicable)

## 3. Missing blockers

- CPU/memory metering for billing (not yet attributed per run in API).
- First-class **upload → validate → build** agent artifact pipeline (beyond install-from-store).
- CI with coverage gate 80%+.

## 4. Launch checklist

- [ ] Staging: `alembic upgrade head`, smoke tests, load test queue at target RPS
- [ ] Prod: managed Postgres + Redis, backups, PITR
- [ ] Dashboard behind HTTPS + same-site cookies
- [ ] On-call runbook + paging for queue backlog SLO

## 5. 30-day founder execution plan

| Week | Focus |
|------|--------|
| 1 | CI + contract tests + staging parity |
| 2 | Deployment service MVP + status API |
| 3 | Observability dashboards + DLQ drill |
| 4 | Billing meters + first paid tier |

## 6. First customer acquisition checklist

- [ ] Single-tenant pilot contract + DPA
- [ ] Shared Slack/Discord support channel SLA
- [ ] Reference architecture doc (one page)
- [ ] Exit criteria for pilot → GA pricing
