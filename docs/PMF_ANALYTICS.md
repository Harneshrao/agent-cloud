# PMF & activation analytics

Measure whether developers complete the first success loop **without founder help**.

---

## 1. Activation model

**Canonical funnel (ordered):**

```
signup_completed
  → project_created
  → artifact_upload_succeeded
  → deployment_created
  → first_task_completed   ← true activation moment
  → trace_viewed
  → api_key_created        ← success-loop complete + retention signal
```

| Milestone | Meaning |
|-----------|---------|
| **Activation** | `first_task_completed` (first successful task for a project) |
| **Success loop complete** | All onboarding steps + API key (client) OR activation + API key |
| **Retention signal** | Return login, trace views, retry clicks, second deploy |

---

## 2. Architecture

| Layer | Path |
|-------|------|
| Table | `product_events` (Alembic `i9j0k1l2m3`) |
| Insert | `database/product_events.py`, `services/product_analytics.py` |
| Aggregates | `services/pmf_metrics.py` |
| API | `POST /analytics/events`, `GET /analytics/pmf/summary` |
| Client | `dashboard/lib/analytics.ts` |
| Founder UI | `dashboard/app/founder/page.tsx` |

**Billing ledger** (`usage_events`) remains separate — used for deployment health & trust metrics (uploads, task outcomes, DLQ).

Every product event supports: `user_id`, `project_id`, `deployment_id`, `task_id`, `session_id`, `onboarding_step`, `properties`, `timestamp`.

---

## 3. Onboarding funnel metrics

`GET /analytics/pmf/summary?days=30` returns:

- Per-step counts & drop-off %
- Activation rate (activated / signups)
- Median time signup → first task
- Deployment health (upload/deploy failures, rollbacks)
- Trust metrics (task success %, retries, DLQ, trace views)

---

## 4. PMF signals

**Positive:** `first_task_completed`, `api_key_created`, `trace_viewed`, `retry_clicked`

**Churn risk:** signup without `project_created`; upload/deploy failures without recovery; high DLQ rate

**Confusion:** long activation latency; deploy without run; feedback rating ≤ 2; `user_research_session_completed` with `needed_help: true` or `would_use_again` ≤ 2

**PMF health score (0–100):** 40% activation + 25% upload success + 25% task success + 10% onboarding proxy

---

## 5. Developer trust metrics

From `usage_events` + product events:

- Task completion reliability
- Retry / DLQ frequency
- Logs & trace engagement
- Deployment rollback count

---

## 6. User feedback

`FeedbackPrompt` on Deployments → `feedback_submitted` with rating 1–5 + comment.

Shown in founder dashboard under recent feedback.

---

## 7. Founder dashboard

- **URL:** `/founder` (sidebar when `NEXT_PUBLIC_FOUNDER_ANALYTICS=1`)
- **Access:** `ENABLE_FOUNDER_ANALYTICS=1` (dev) or `FOUNDER_EMAILS` or `is_admin`

`run_all.py` enables both flags locally.

---

## 8. Implementation phases

| Phase | Scope |
|-------|--------|
| **P0** | `product_events`, server + client instrumentation, PMF summary API, founder page |
| **P1** | Retention cohorts, failure clustering, page-view funnel |
| **P2** | Predictive churn, onboarding optimization |

---

## 9. Ops

```bash
alembic upgrade head   # includes i9j0k1l2m3
```

Env:

```bash
ENABLE_FOUNDER_ANALYTICS=1
FOUNDER_EMAILS=you@company.com
NEXT_PUBLIC_FOUNDER_ANALYTICS=1
```
