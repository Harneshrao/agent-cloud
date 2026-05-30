# Security hardening (P0)

## Production environment

```bash
ENVIRONMENT=production
JWT_SECRET=<random-64-chars>
ALLOW_ANONYMOUS_DEV=0
REQUIRE_DOCKER_FOR_DEPLOYMENTS=1
USE_DOCKER_RUNTIME=1
AGENT_TIMEOUT_SECONDS=60
WEBHOOK_SECRET=<hmac-secret>
```

## Emergency switches

| Env | Effect |
|-----|--------|
| `DISABLE_TASK_ENQUEUE=1` | Reject all new enqueues |
| `DISABLE_PRODUCTION_GUARD=1` | Skip startup safety checks (break-glass only) |
| `ENABLE_PROJECT_RATE_LIMIT=0` | Disable per-project API bucket |

## Webhooks

Require `X-Project-ID` + `X-Signature` (HMAC). Tasks enqueue only for that project's triggers.

## API keys

`Authorization: Bearer ak_live_...` — same as JWT for authenticated routes.

## Upload

All zip extraction uses `agent_runtime.safe_extract.safe_extract_zip` — never `extractall` on untrusted archives.

Full architecture: `docs/SECURITY_ARCHITECTURE.md`.
