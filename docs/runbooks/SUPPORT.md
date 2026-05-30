# Alpha support playbook

Founder-facing steps for private alpha. **Goal:** unblock activation in <30 minutes.

---

## Triage order

1. Can they reach `/health`?
2. Active project selected (top bar)?
3. `task_id` or `deployment_id` if runtime issue
4. Check `/founder` for correlated failures

---

## Onboarding stuck

| Symptom | Check | Fix |
|---------|-------|-----|
| No project | `/projects` empty | Create project, select in topbar |
| Banner stuck at 1/5 | `product_events` onboarding_step | Walk sample deploy |
| “Project required” | localStorage `agent_cloud_project_id` | Reselect project |

---

## Failed deploy

1. Ask: sample echo or custom ZIP?
2. Dashboard → Deployments error (now classified)
3. API: `GET /deployments/{id}/events`
4. Common causes:
   - Invalid `agent.yaml` / missing `agent.py`
   - Quota (`429`) → `/limits`
   - Path traversal / unsafe ZIP (security layer)

**Reply template:**

> We saw a deploy validation error. Open Deployments → try **Deploy sample echo** first. If custom ZIP, ensure `agent.yaml` + `agent.py` at zip root. Send us the error text from the red banner if it persists.

---

## Task debugging

1. **Runs** → open task → trace
2. Check status: `queued` / `running` / `failed` / `dead`
3. `GET /observability/tasks/{task_id}/trace`
4. If `running` forever → worker/Redis (incidents runbook)

**Reply template:**

> Open Runs → your task → full trace. If status is failed, the error block shows the agent exception. Paste the task ID (UUID) and we'll check worker logs.

---

## DLQ recovery

DLQ = tasks that exhausted retries.

1. Explain: “Your agent raised an error repeatedly; we parked the task so nothing else stalls.”
2. User fixes agent → **new run** from Deployments (not DLQ replay unless you add it)
3. Founder: check DLQ count in `/founder` alerts

---

## Quota confusion

1. User → **Limits** page
2. Founder: `GET /billing/summary` with their `X-Project-ID`
3. Alpha: manual bump or reset window — document in invite

---

## Runtime crashes

1. Identify deployment version
2. Rollback: Deployments → Rollback (or redeploy previous artifact)
3. If platform-wide: incidents runbook

---

## Escalation

| Condition | Action |
|-----------|--------|
| Blocked >30 min | Live session |
| Data wrong / security | S0 — stop new invites |
| Same bug ≥3 users | P0 engineering fix |

Log every ticket: user email, project_id, task_id, one-line root cause.
