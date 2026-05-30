# Activation loop (Wave 1)

Canonical path every alpha tester should complete without founder help:

**Deploy → Run → Trace → Trust → Repeat**

## Product surfaces

| Step | Screen | Success signal |
|------|--------|----------------|
| 1. Deploy | Deployments → sample echo | `deployment_created` |
| 2. Run | Post-deploy **Run your first task** | `first_task_completed` |
| 3. Trace | Runs & traces → execution trace | `trace_viewed` |
| 4. Trust | Result + logs visible; recovery on failure | feedback / no help needed |
| 5. Repeat | **Run again** on trace | `second_task_started` |
| 6. API key | API keys (after first success) | `api_key_created` |

## UX principles

- **One nav label for executions:** Runs & traces (not separate Runs vs Logs).
- **Post-deploy:** inline “Next step” when deploy exists but no runs yet.
- **Trace page:** status + result first, logs second, technical timeline collapsed.
- **Failure:** amber recovery panel with Run again + redeploy links.
- **After success:** TracePostSuccessPanel — Run again + Create API key.

## Founder analytics (`/founder`)

- **Activation gaps:** deploy-without-run, run-without-trace, trace-without-key, repeat rate.
- **Ops alerts:** auto-fire on gap patterns and DLQ spikes.

## Pre-tester checklist

```bash
py -3.11 scripts/dev_doctor.py --readiness
```

Must print **READY FOR TESTER** including second run smoke.

## Post-session

```bash
py -3.11 scripts/user_research_report.py
```

Score with `docs/templates/USER_SESSION_SCORECARD.md`.
