# User feedback & interviews (alpha)

Avoid roadmap chaos. Learn trust and friction.

**First 5 users program:** [`FIRST_5_USERS.md`](../FIRST_5_USERS.md) · Scorecard: [`templates/USER_SESSION_SCORECARD.md`](../templates/USER_SESSION_SCORECARD.md)

---

## When to interview

- After first deploy (day 0–1)
- After first failure (DLQ or deploy error)
- Day 3 if no `api_key_created`
- Any `feedback_submitted` with rating ≤2

---

## 15-minute script

1. **Context** (2 min): What were you trying to automate?
2. **First impression** (3 min): Where did you hesitate on the dashboard?
3. **Deploy** (4 min): Sample vs ZIP? What confused you?
4. **Run & debug** (4 min): Did logs/traces feel sufficient?
5. **Trust** (2 min): Would you run production traffic? Why / why not?

**Do not** pitch features. Ask: “What would make you use this again tomorrow?”

---

## Capture

| Field | Where |
|-------|--------|
| Rating + quote | `FeedbackPrompt` → `product_events` |
| Notes | Spreadsheet or Notion |
| PMF signal | Tag: activation / trust / confusion |

---

## Feature request filter

Ask: “Is this blocking your **first successful run**?”

- Yes → P0 candidate
- No → post-PMF backlog

---

## Trust signals to note

| Positive | Negative |
|----------|----------|
| Returned without ping | Gave up after deploy |
| Created API key unprompted | “I don't trust it with prod” |
| Debugged via trace alone | Needed founder to read logs |

---

## Weekly synthesis (30 min)

1. `/founder` — funnel, alerts, feedback
2. Top 3 friction themes
3. One engineering fix for next week
4. Update [`ALPHA_PRIVATE.md`](../ALPHA_PRIVATE.md) if targets shift
