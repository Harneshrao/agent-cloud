# First 5 users — PMF learning system

**Company milestone:** Learn whether real developers can **deploy → run → debug** confidently **without you**.

Not shipping features. Running structured user research with 5 external developers.

---

## Quick links

| Asset | Path |
|-------|------|
| Tester invite (send as-is) | [`ALPHA_TEST_INVITE.md`](ALPHA_TEST_INVITE.md) |
| Exact test script | [`ALPHA_TEST_SCRIPT.md`](ALPHA_TEST_SCRIPT.md) |
| Per-session scorecard (copy ×5) | [`templates/USER_SESSION_SCORECARD.md`](templates/USER_SESSION_SCORECARD.md) |
| Observation log (during session) | [`templates/USER_OBSERVATION_LOG.md`](templates/USER_OBSERVATION_LOG.md) |
| Issue triage (after each user) | [`templates/ISSUE_TRIAGE.md`](templates/ISSUE_TRIAGE.md) |
| Founder metrics | `/founder` + `py -3.11 scripts/user_research_report.py` |
| Pre-test health gate | [`DEV_HEALTHCHECK.md`](DEV_HEALTHCHECK.md) |

---

## 1. User test plan

### Ideal tester profile

| Must have | Nice to have |
|-----------|--------------|
| Backend or platform engineer | Has a real agent/script to run later |
| Comfortable with Python | Uses CI or scripts daily |
| Will talk for 15 min unassisted first | Will do 15-min follow-up interview on day 3 |
| Will give blunt feedback | Tolerates alpha rough edges |

**Avoid for first 5:** pure frontend devs with no Python, people who only want chat/LLM wrappers, anyone who needs hand-holding through every click.

### Session design

| Parameter | Value |
|-----------|-------|
| **Cohort size** | 5 users (Wave 0) |
| **Unassisted session** | 15 minutes |
| **Founder intervention** | Only if blocked >5 min or hard error |
| **Follow-up** | 15-min interview day 3 ([`runbooks/FEEDBACK.md`](runbooks/FEEDBACK.md)) |
| **Observation** | Async preferred; live screen-share optional for user 1–2 |

### Exact task flow

See [`ALPHA_TEST_SCRIPT.md`](ALPHA_TEST_SCRIPT.md) — same as alpha invite:

1. Create/select project  
2. Deploy sample echo  
3. Run first task  
4. Open execution trace  
5. (Optional) sample_fail → Failed tasks → recover  
6. Create API key  
7. In-product session feedback (API keys page)

### Observation method

- **Silent async:** Send invite, review `/founder` + scorecard after 24h  
- **Live (recommended for users 1–2):** Screen share, think-aloud, fill [`USER_OBSERVATION_LOG.md`](templates/USER_OBSERVATION_LOG.md)  
- **Never:** Lead the clicks unless they are blocked

### Success criteria (per user)

| Criterion | Pass |
|-----------|------|
| Deploy sample echo | Active deployment visible |
| First run | Task reaches `completed` |
| Trace | Opens trace/logs without founder help |
| Trust | User says they believe it worked (think-aloud or rating ≥4) |
| Loop complete | API key created OR explicit “would use again” ≥4 |

**Cohort success (after 5):** ≥3/5 complete full loop without founder help; ≥3/5 “would use again” ≥4.

---

## 2. Test script

Copy from [`ALPHA_TEST_SCRIPT.md`](ALPHA_TEST_SCRIPT.md). Send with:

- Hosted URL (not localhost unless dev tester)
- Single support channel (Slack/email)
- “No help unless blocked” rule

**Before send:** `py -3.11 scripts/dev_doctor.py --readiness` → **READY FOR TESTER**

---

## 3. Observation framework

Track during session (see [`USER_OBSERVATION_LOG.md`](templates/USER_OBSERVATION_LOG.md)):

| Signal | Examples |
|--------|----------|
| **Hesitation** | Pauses >10s, reads sidebar, hovers without clicking |
| **Wrong click** | Logs vs Runs, Workers, Usage before deploy |
| **Confusion** | “Did it work?”, “Where are logs?”, “What’s a project?” |
| **Abandonment** | Closes tab mid-flow, skips optional, no return in 24h |
| **Trust break** | “Is it broken?”, generic 500, green success then failure |
| **Question asked** | Log verbatim — highest-signal data |

### Severity ranking

| Level | Definition | Example |
|-------|------------|---------|
| **S0 — Launch blocker** | Cannot complete core loop | Run 500, deploy never activates |
| **S1 — Trust break** | Completes but doesn’t believe it | No trace, ambiguous status |
| **S2 — Friction** | Completes with confusion | Duplicate nav labels, unclear next step |
| **S3 — Nice-to-have** | Preference / polish | Dark mode, copy tweak |

**Rule:** Only fix **repeated S0–S2** across ≥2 users. One-off → note, don’t sprint.

---

## 4. Feedback capture

### Automatic (in product)

| Source | Event | Where |
|--------|-------|-------|
| Funnel | `signup_completed` … `api_key_created` | `/founder` |
| Step feedback | `feedback_submitted` | Deployments post-success |
| Session PMF | `user_research_session_completed` | API keys after first key |
| Onboarding | `onboarding_step` | localStorage + analytics |

### Manual (founder)

| Field | Store in |
|-------|----------|
| Quotes | Scorecard “Verbatim quotes” |
| Screenshots | Slack thread / scorecard link |
| Completion time | Scorecard + `/founder` median TTA |
| Needed help? | Scorecard + session event `needed_help` |
| Observation notes | [`USER_OBSERVATION_LOG.md`](templates/USER_OBSERVATION_LOG.md) |

**Lightweight storage:** One scorecard file (or Notion row) per user. No new database tables for Wave 0.

---

## 5. PMF scorecard

### Cohort metrics (track after each user)

| Metric | Target (5 users) | Source |
|--------|------------------|--------|
| Deploy success % | 100% | `deployment_created` / attempts |
| First run success % | ≥80% | `first_task_completed` |
| Time to first success | ≤15 min median | funnel timestamps |
| Needed help count | ≤1 of 5 | scorecard + session event |
| Would use again (≥4) | ≥3 of 5 | session feedback |
| Trace viewed | ≥4 of 5 | `trace_viewed` |
| API key created | ≥3 of 5 | `api_key_created` |

### Per-user scorecard

Copy [`templates/USER_SESSION_SCORECARD.md`](templates/USER_SESSION_SCORECARD.md) for each tester.

### CLI rollup

```bash
py -3.11 scripts/user_research_report.py
py -3.11 scripts/user_research_report.py --days 14
```

---

## 6. Issue triage

After **each** user, fill [`templates/ISSUE_TRIAGE.md`](templates/ISSUE_TRIAGE.md).

| Class | Action |
|-------|--------|
| **Launch blocker** | Fix before next user |
| **Friction** | Log; fix if 2+ users hit same issue |
| **Nice-to-have** | Post-PMF backlog |

**Weekly synthesis (30 min):**

1. `/founder` — funnel, alerts, recent feedback  
2. Top 3 friction themes from scorecards  
3. **One** engineering fix for next week  
4. Update [`ALPHA_PRIVATE.md`](ALPHA_PRIVATE.md) if targets shift  

---

## 7. Founder dashboard hooks

**URL:** `/founder` (when `NEXT_PUBLIC_FOUNDER_ANALYTICS=1`)

| Signal | Where |
|--------|-------|
| Activation drop | Funnel bar + `activation_stall` alert |
| Confusion clusters | Low feedback ratings + `negative_feedback` alert |
| Failures | Deployment health + `deploy_failures`, `task_reliability` |
| Trust issues | DLQ spike, task success %, trace views vs runs |
| **First 5 cohort** | “User research cohort” table (recent users × funnel steps) |

**Before each invite:** `scripts/dev_doctor.py --readiness`

---

## 8. Iteration loop

```
Invite user N
    → readiness check (founder)
    → user runs unassisted (15 min)
    → in-product feedback + scorecard
    → triage (blocker / friction / nice-to-have)
    → if blocker: fix before N+1
    → if repeated friction (2+): prioritize fix
    → retest fix with next user OR quick smoke with dev_doctor
    → repeat until N=5
    → cohort review: go/no-go Wave 1 (10–15 users)
```

**During testing:** No new features. Only fixes for repeated S0–S2.

---

## 9. Implementation plan

| Priority | Deliverable | Status |
|----------|-------------|--------|
| **P0** | This doc + test script + scorecard templates | ✓ |
| **P0** | Observation + triage templates | ✓ |
| **P0** | `user_research_report.py` CLI | ✓ |
| **P1** | Session feedback on API keys page | ✓ |
| **P1** | Feedback prompt post-deploy | ✓ |
| **P1** | Founder cohort table | ✓ |
| **P2** | Repeatable Wave 1 playbook + automated cohort export | Backlog |

---

## First-time user audit (external perspective)

| Step | Clarity | Risk |
|------|---------|------|
| Signup / project | Good empty states; top bar project select can feel like an error if empty | Medium |
| Deployments | Strong sample echo CTA | Low |
| Run task | Auto-redirect to trace is good | Low if run works |
| Trace / logs | “Runs & traces” unified — better than split Logs | Medium (label familiarity) |
| Failed tasks | Reassuring copy; recovery path still multi-step | Medium |
| API keys | Curl example pre-filled helps | Low |
| Docs | QUICKSTART long; invite script is better for first 5 | Medium |
| Founder dashboard | Funnel + alerts sufficient for Wave 0 | Low |

**Biggest remaining product risk:** Local/hosted infra looks like product failure — use [`DEV_HEALTHCHECK.md`](DEV_HEALTHCHECK.md) before every session.
