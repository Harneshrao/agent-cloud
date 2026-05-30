# Private alpha — strategy & readiness

**Company test:** Will real developers repeatedly trust Agent Cloud to deploy and run agents?

Infrastructure is ahead of PMF certainty. This doc is the operating model for learning from real users fast.

---

## 1. Private alpha strategy

### Ideal alpha user

- Backend or platform engineer (Python familiarity)
- Has an agent or script they want to run reliably (not just chat demos)
- Willing to give 30 minutes + async Slack feedback
- Tolerates rough edges if deploy → run → logs works

### Ideal cohort size

| Phase | Users | Duration |
|-------|-------|----------|
| **Wave 0** | 3–5 (founder friends) | 1 week — fix launch blockers |
| **Wave 1** | 10–15 | 2–3 weeks — measure activation |
| **Wave 2** | 25–30 max | 4 weeks — retention + trust |

### Onboarding strategy

1. **White-glove for Wave 0:** 15-min screen share using [`QUICKSTART.md`](../QUICKSTART.md)
2. **Self-serve for Wave 1+:** Dashboard first-success loop + sample echo deploy
3. **Never** ask users to set `X-Project-ID` — project selector only

### Rollout sequencing

```
Invite → signup → project → sample deploy → first run → trace → API key → interview (day 3)
```

### Feedback loop (weekly)

| Day | Founder action |
|-----|----------------|
| 0 | Invite + confirm API URL / health |
| 1 | Check `/founder` funnel drop-off |
| 3 | 15-min interview (see `runbooks/FEEDBACK.md`) |
| 7 | PMF score review + prioritize 1 reliability fix |

### Support expectations (alpha)

- Response: **<4h business hours** for blockers, next-day for non-blockers
- Channel: Slack or email (single channel)
- No SLA — set expectation: “alpha, we fix fast”

---

## 2. Alpha readiness checklist

### Launch blockers (must fix before Wave 1)

| Item | Status |
|------|--------|
| API reachable from dashboard (`NEXT_PUBLIC_API_URL` → port **8000**, not 3000) | Verify per user |
| Sample deploy works (`POST /deployments/onboarding/sample/sample_echo`) | Required |
| First task completes and trace loads | Required |
| Errors are productized (no raw `run_all.py` in UI) | Implemented |
| Migrations applied (`alembic upgrade head`) | Required |
| Postgres + Redis up | Required |

### Medium risks (acceptable with playbook)

| Item | Mitigation |
|------|------------|
| DLQ confusion | `runbooks/SUPPORT.md` § DLQ |
| Quota surprises | Point to `/limits` |
| Rollback rarely used | Document when to redeploy vs rollback |
| Dark-mode contrast | Fix as reported |

### Acceptable alpha risks

- No billing self-serve upgrade
- No multi-region
- Founder-only PMF dashboard
- Manual quota bumps

---

## 3. Support operations

See [`runbooks/SUPPORT.md`](runbooks/SUPPORT.md) — playbooks for deploy fail, task debug, DLQ, quota.

**Escalation:** User blocked >30 min → founder pairs live → file GitHub issue with `task_id` / `deployment_id`.

---

## 4. Incident operations

See [`runbooks/INCIDENTS.md`](runbooks/INCIDENTS.md) — worker/Redis outage, queue recovery, kill switches.

**Severity:**

| Level | Example | Response |
|-------|---------|----------|
| S0 | Data loss, auth bypass | Stop invites, fix immediately |
| S1 | No tasks processing | All-hands, status to alpha Slack |
| S2 | Elevated failures | Triage in `/founder`, patch <24h |
| S3 | Single-user deploy fail | Support playbook |

---

## 5. Feedback system

See [`runbooks/FEEDBACK.md`](runbooks/FEEDBACK.md) and **[`FIRST_5_USERS.md`](FIRST_5_USERS.md)** (Wave 0 — first 5 external developers).

**Rules:**

- One interview script — don't rebuild features in the call
- Log insights as `feedback_submitted` + notes doc
- Filter feature requests → “post-PMF backlog”

---

## 6. PMF validation framework

### Targets (Wave 1, 14 days)

| Metric | Target | Source |
|--------|--------|--------|
| Activation rate | ≥40% signups → `first_task_completed` | `/founder` |
| Upload success | ≥80% | deployment health |
| Task success | ≥85% completed / (completed+failed) | trust metrics |
| Median time to activation | ≤15 min | funnel |
| Week-1 return | ≥30% login again | `login_completed` |

### PMF-positive signals

- Second deploy without support
- API key created without prompting
- User sends curl example back to you

### Weak-wedge signals

- Signups without `project_created`
- Deploy without `first_task_completed`
- DLQ > completed tasks
- Low feedback scores (≤2)

---

## 7. Launch surface

| Surface | Principle |
|---------|-----------|
| Dashboard nav | Deploy → Run → Logs (no marketplace clutter) |
| Empty states | One primary CTA each |
| Errors | `PlatformAlert` — what / fault / next step |
| Docs | [`QUICKSTART.md`](../QUICKSTART.md) is canonical |
| API docs | `/docs` — deployment-first paths |

---

## 8. Founder dashboard

**URL:** `/founder` (when `NEXT_PUBLIC_FOUNDER_ANALYTICS=1`)

- Funnel + PMF health score
- **Alpha ops alerts** — deploy failures, DLQ spike, activation stall, negative feedback
- Targets block for weekly review

---

## 9. Implementation plan

| Priority | Item |
|----------|------|
| **P0** | This doc + runbooks + error UX fixes + ops alerts |
| **P1** | Wave 0 interviews + env checklist in invite email |
| **P2** | Automated onboarding diagnostics |

---

## Likely support tickets (prepare answers)

1. “Deployments page says Not Found” → wrong `NEXT_PUBLIC_API_URL` or API not running
2. “Sample deploy failed” → ZIP/manifest or quota — check deployment events
3. “Task stuck running” → worker/Redis — `runbooks/INCIDENTS.md`
4. “What is DLQ?” → failed tasks after retries — link to trace
5. “Hit quota” → `/limits` + founder manual bump

---

## Environment checklist (send to each alpha user)

```bash
# 1. Clone + install
py -3.11 run_all.py   # starts API :8000, dashboard :3000

# 2. Dashboard .env.local
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
NEXT_PUBLIC_DEV_HINTS=1

# 3. Verify
curl http://127.0.0.1:8000/health
```

If API binds to **8001**, set `NEXT_PUBLIC_API_URL=http://127.0.0.1:8001`.
