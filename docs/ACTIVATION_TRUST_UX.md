# Activation flow & trust-centered UX

Developers trust Agent Cloud when success feels smooth, failures feel recoverable, and the next action is obvious.

---

## 1. Refined first-success journey

| Step | Emotional goal | Primary CTA |
|------|----------------|-------------|
| Create project | “I have a workspace” | Create / select project |
| Deploy agent | “Something is live” | Deploy sample echo |
| Run first task | “It actually runs” | **Run your first task** (hero) |
| View logs | “I can debug” | Open trace / Runs |
| Retry failure | “Recoverable” | DLQ → trace → redeploy |
| API key | “I can automate” | Create key |

Implemented: `PostDeployPanel`, `DeploymentRow`, slimmer `FirstSuccessBanner` on deployments after deploy.

---

## 2. Post-deploy experience

After deploy, the deployments page shows:

- Green success strip: “Deployment active — ready to execute tasks.”
- Hero **Run your first task** button
- Links: View runs, View logs, Create API key
- Recent activity (last 3 tasks) or nudge to run first task

---

## 3. CTA hierarchy

1. Run first task (primary button, large)
2. View runs / logs (secondary chips)
3. Restore previous (tertiary, renamed from Rollback)
4. Deploy another version (collapsed `<details>`)
5. Previous packages (collapsed)

---

## 4. Degraded mode

| Before | After |
|--------|--------|
| API unavailable (amber/red banner) | Live features reconnecting (slate, calm) |
| Top bar dominates | Compact strip; expandable technical details |

Components: `PlatformNotice`, `ApiStatusBar`, `kind: degraded` in `platform-errors.ts`.

---

## 5. Error semantics

All errors include:

- **dataSafe** — “Your data is safe” when true
- **hint** — next action
- **diagnostic** — dev-only, collapsed under “Technical details”

No `run_all.py` in primary copy unless `NEXT_PUBLIC_DEV_HINTS=1`.

---

## 6. Deployment history language

| Internal | User-facing |
|----------|-------------|
| Your deployments | Live agents / hero panel |
| Uploaded versions | Previous packages (collapsed) |
| Status: active | Ready to run |
| Rollback | Restore previous |
| Artifact validated | Ready to deploy |
| DLQ (nav) | Failed tasks |

---

## 7. Post-deploy momentum

`fetchObservabilityTasks(8)` on deployments load → recent activity in `PostDeployPanel`.

---

## 8. Micro-trust wins (P0)

| Issue | Fix |
|-------|-----|
| Error banner over success | Soft notice when deployments exist |
| Onboarding banner dominates | Compact on `/deployments` after deploy |
| Run task buried | Hero CTA |
| Infra nav label DLQ | Failed tasks |
| Alarm colors on offline | Slate degraded strip |

---

## 9. Success reinforcement

`SuccessBanner` + `SUCCESS_MESSAGES` in `lib/trust-copy.ts` — restrained green confirmations, no gamification.

---

## 10. Roadmap

| Phase | Items |
|-------|--------|
| **P0** | Done — degraded copy, post-deploy panel, CTA hierarchy, history reframe |
| **P1** | Live log preview on deploy page; guided run walkthrough |
| **P2** | Adaptive next-step engine from `product_events` |

---

## Files

```
dashboard/lib/trust-copy.ts
dashboard/lib/platform-errors.ts
dashboard/components/product/platform-notice.tsx
dashboard/components/product/platform-alert.tsx
dashboard/components/product/post-deploy-panel.tsx
dashboard/components/product/deployment-row.tsx
dashboard/components/product/success-banner.tsx
dashboard/app/deployments/page.tsx
```
