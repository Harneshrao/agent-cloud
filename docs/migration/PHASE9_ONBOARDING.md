# Design partner — onboarding & support

## Onboarding checklist

1. Create account (`POST /register` + dashboard `/signup`).
2. Create project (`POST /projects`).
3. Set `X-Project-ID` / JWT for API calls.
4. Install or register agent (`/agents/installations` or upload path when enabled).
5. Run agent (`POST /agents/v2/run` or installation run).
6. Verify run in dashboard `/runs` and `/logs`.
7. Create API key (`POST /api-keys`) for automation.

## Bug report workflow

1. Capture `X-Request-ID` from response headers (when trace middleware enabled).
2. Note `task_id` (UUID) and deployment/installation id.
3. Export `/system/*` readouts for queue depth and worker health (admin).

## Support workflow

1. Reproduce with minimal curl + env (`SKIP_MIGRATION_CHECK` off in staging only).
2. Check Postgres `tasks`, `task_events`, `dead_letter_queue`.
3. Check Redis `queue:ready`, `queue:processing`, locks.

## Feature request workflow

1. One paragraph user story + acceptance criteria.
2. Confirm wedge alignment (hosting/runtime only).
3. Size against queue/Postgres migration risk.
