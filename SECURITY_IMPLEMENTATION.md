# Security Hardening Implementation

This document summarizes the backend security changes applied after the Red Team penetration test. The backend is now **secure, resilient, and safe for public exposure** while preserving existing platform functionality.

---

## 1. Secure Agent Execution Endpoint

**Endpoint:** `GET /agent/run`

**Change:** The endpoint now requires **authentication and project context**. It uses the existing `require_project_context` dependency (which implies `get_current_user` and `X-Project-ID` or `project_id` query). Tasks are enqueued with the caller’s `project_id` so they are subject to quota and project scoping.

**Files modified:** `api/main.py`

**Behavior:** Only authenticated users who can access a project can enqueue tasks. Request must include `Authorization: Bearer <token>` and `X-Project-ID` (or `project_id` query). Unauthorized callers receive 401 or 403.

---

## 2. Secure Task Result Endpoints

**Endpoints:** `GET /task/{task_id}`, `GET /tasks/{task_id}/stream`, `GET /task/{task_id}/runs`

**Change:** All three require **project context** and a **project-level access check**. The task’s `project_id` is read from the database; if it does not match the caller’s project, the response is **403 Access denied**. If the task is not found, **404** is returned.

**Files modified:** `api/main.py`

**Helper:** `_assert_task_project_access(task_id, project_id)` centralizes the check and logs 403 via the security logger.

---

## 3. Protect System Observability Endpoints

**Endpoints:** All under `/system/*` (e.g. `/system/metrics`, `/system/workers`, `/system/queue`, `/system/containers`, `/system/recovery`, `/system/autoscaler`, `/system/dead_letters`, `/system/alerts`, `/system/health`).

**Change:** Every system route now uses the **`require_admin`** dependency. Only users whose email is listed in the `ADMIN_EMAILS` environment variable can access these endpoints.

**Files modified:** `api/deps.py` (new `require_admin`), `api/system_api.py` (all routes)

**Configuration:** Set `ADMIN_EMAILS=admin@example.com,ops@example.com` (comma-separated). Admins must still authenticate with a valid Bearer token.

---

## 4. Secure Webhook Endpoints

**Endpoint:** `POST /webhooks/{source}`

**Change:** **Webhook signature verification** is required using HMAC-SHA256.

- **Header:** `X-Signature` must be the hex-encoded HMAC-SHA256 of the **raw request body** using a shared secret.
- **Secret:** From environment variables:
  - `WEBHOOK_SECRET` — used for all sources if set.
  - `WEBHOOK_SECRET_<SOURCE>` — per-source override (e.g. `WEBHOOK_SECRET_GITHUB`).
- Invalid or missing signature → **401** and the event is **logged** (failed webhook verification).
- If no secret is configured → **501** so callers know verification is not enabled.

**Files modified:** `api/webhook_api.py`

**Client usage:** Compute `HMAC-SHA256(secret, raw_body)` and send as `X-Signature: <hex>`.

---

## 5. Rate Limiting

**Change:** A **global rate limit middleware** runs on every request (by client IP, or `X-Forwarded-For` when behind a proxy).

| Path / pattern      | Limit (per minute) |
|---------------------|--------------------|
| `/agent/run`        | 20                 |
| `/webhooks/*`       | 60                 |
| All other API paths | 100                |

When exceeded, the response is **429 Too Many Requests** with body `{"detail": "Too many requests", "retry_after": 60}` and header `Retry-After: 60`. Each violation is **logged** (rate_limit_exceeded).

**Files modified:** `api/rate_limit.py` (new), `api/main.py` (middleware registered)

---

## 6. Protect File Access Tools

**Tool:** `file_reader` in `tools/tool_executor.py`

**Change:** File access is **restricted to a single sandbox directory**:

- **Default root:** `./workspace` (relative to process CWD), overridable with `FILE_READ_ROOT`.
- Resolved path must be **under** the sandbox root (using `os.path.commonpath` so `..` and symlinks cannot escape).
- Any attempt to read outside the sandbox returns a generic error and is **logged** (event: `file_reader_sandbox_denied`).

**Files modified:** `tools/tool_executor.py` (already enforced; added structured logging for denials)

---

## 7. Prevent SSRF in URL-Fetching Tools

**Tools:** `web_scraper`, `api_caller` in `tools/tool_executor.py`

**Change:** URL validation and request limits:

- **Protocols:** Only `http` and `https` are allowed (e.g. `file://` rejected).
- **Blocked hosts:** localhost, 127.0.0.1, 169.254.169.254, 10.x.x.x, 192.168.x.x, 172.16–31.x.x, and IPv6 equivalents (link-local, private).
- **Request timeout:** 15 seconds.
- **Max response size:** 512 KB for both tools.

**Files modified:** `tools/tool_executor.py` (already in place; behavior documented here)

---

## 8. Security Logging

**Change:** **Structured security events** are logged for audit and incident response.

**New file:** `api/security_logger.py`

**Events logged:**

| Event                      | When |
|----------------------------|------|
| `failed_webhook_verification` | Webhook `X-Signature` invalid or missing |
| `unauthorized_access`         | 401 (missing/invalid token) or 403 (forbidden) |
| `rate_limit_exceeded`         | Client exceeds rate limit (429) |
| `file_reader_sandbox_denied`  | Path outside sandbox (in tools layer) |

**Usage:** The app uses the standard `"security"` logger. Configure your logging framework to capture this logger (e.g. to a file or SIEM). Optional: set `SECURITY_LOG_JSON=1` for JSON-style output if needed.

**Where logging is called:** `api/auth_api.py` (401), `api/deps.py` (403 for project/admin), `api/webhook_api.py` (failed verification), `api/rate_limit.py` (429), `api/main.py` (403 task access), `tools/tool_executor.py` (sandbox deny).

---

## 9. List of Modified and New Files

| File | Change |
|------|--------|
| **api/main.py** | Rate limit middleware; `/agent/run` requires project context and passes `project_id` to `enqueue_task`; `/task/{id}`, `/tasks/{id}/stream`, `/task/{id}/runs` require project context and task–project access check. |
| **api/auth_api.py** | `get_current_user` takes `Request`; logs 401 (missing/invalid token) via security logger. |
| **api/deps.py** | Added `require_admin` (checks `ADMIN_EMAILS`); 403 for project denied now logged. |
| **api/system_api.py** | All routes protected with `Depends(require_admin)`. |
| **api/webhook_api.py** | Raw body read; HMAC-SHA256 verification of `X-Signature`; 401 on failure and logging; 501 if no secret configured. |
| **api/rate_limit.py** | **New.** In-memory sliding-window rate limiter; middleware applies limits by path; 429 and logging on exceed. |
| **api/security_logger.py** | **New.** Structured security logging (webhook failure, unauthorized access, rate limit, optional JSON). |
| **tools/tool_executor.py** | File sandbox default and behavior documented; logging when file_reader denies path outside sandbox. SSRF rules already present. |

---

## 10. Environment Variables (Security-Related)

| Variable | Purpose |
|----------|---------|
| `ADMIN_EMAILS` | Comma-separated emails allowed to access `/system/*`. |
| `WEBHOOK_SECRET` | Shared secret for webhook HMAC (all sources). |
| `WEBHOOK_SECRET_<SOURCE>` | Per-source webhook secret (e.g. `WEBHOOK_SECRET_GITHUB`). |
| `FILE_READ_ROOT` | Sandbox root for `file_reader` (default `./workspace`). |
| `ALLOW_ANONYMOUS_DEV` | If `1`/`true`/`yes`, bypasses auth for local dev; **set to `0` in production.** |
| `SECURITY_LOG_JSON` | If `1`/`true`/`yes`, security log can emit JSON (if implemented in handler). |

---

## 11. Backward Compatibility and Deployment

- **Dashboard / clients:** Must send `Authorization: Bearer <token>` and `X-Project-ID` for `/agent/run` and task endpoints. Existing project-scoped flows already do this when not using `ALLOW_ANONYMOUS_DEV`.
- **Webhooks:** Callers must compute and send `X-Signature`. Configure `WEBHOOK_SECRET` (or per-source) before enabling production webhooks.
- **System/health:** If a load balancer hits `/system/health`, it must use an admin user’s token, or you can expose a separate public health check (e.g. `GET /healthz`) that returns 200 without details.
- **Rate limits:** Applied per client IP (or first `X-Forwarded-For`). Ensure proxies set `X-Forwarded-For` correctly so limits are per client, not per proxy.

---

*Implementation completed. For questions or further hardening, refer to the Red Team report and this document.*
