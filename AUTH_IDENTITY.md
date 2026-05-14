# Authentication and Authorization System

This document describes the **identity layer** implemented for the AI automation platform: user accounts, JWT, API keys, project-level permissions, and admin roles.

---

## 1. Database Migrations

**File:** `database/migrations.py`

**Run:** Migrations run automatically on API startup (`run_migrations()` in `api/main.py`).

**Changes:**

- **users**
  - `ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0`
  - `ALTER TABLE users ADD COLUMN status TEXT NOT NULL DEFAULT 'active'`
- **project_members** (new table)
  - `id`, `project_id`, `user_id`, `role` (owner | member | viewer), `created_at`
  - `UNIQUE(project_id, user_id)`, indexes on `project_id`, `user_id`
- **api_keys** (new table)
  - `id`, `user_id`, `key_hash`, `name`, `created_at`, `last_used_at`
  - Index on `user_id`, unique on `key_hash`

**Backward compatibility:** Existing `users` rows get `is_admin=0`, `status='active'`. Passwords remain valid for existing rows until re-registration in the new auth system.

---

## 2. Users Table (Effective Schema)

| Column         | Type    | Notes                          |
|----------------|---------|--------------------------------|
| id             | INTEGER | PK                             |
| email          | TEXT    | UNIQUE, stored lowercased     |
| password_hash  | TEXT    | SHA-256 hash                    |
| name           | TEXT    | Optional                       |
| is_admin       | INTEGER | 0 or 1                         |
| status         | TEXT    | e.g. `active`                  |
| created_at     | TIMESTAMP |                              |

---

## 3. Login System

**Endpoints:**

- **POST /auth/register**  
  - Body: `email`, `password`, `name` (optional).  
  - Password: min 8 characters; optional complexity (uppercase, number, symbol) if `PASSWORD_REQUIRE_COMPLEXITY=1`.  
  - Passwords hashed with **SHA-256**.  
  - Returns: `{ "user": {...}, "message": "Registered successfully" }`.

- **POST /auth/login**  
  - Body: `email`, `password`.  
  - Verifies password (SHA-256), checks `status == 'active'`.  
  - Returns **JWT** and user (no session token in response; session table still used for legacy tokens).

**JWT:**

- **Algorithm:** HS256.  
- **Secret:** `JWT_SECRET` env (default `change-me-in-production`; **must** be set in production).  
- **Expiration:** 24 hours (`JWT_EXPIRATION_HOURS`).  
- **Payload:** `user_id`, `email`, `is_admin`, `exp`, `iat`.  
- **Usage:** Client sends `Authorization: Bearer <jwt>`.

**Security:** Failed logins and invalid JWT are logged (see Logging).

---

## 4. Auth Dependency: get_current_user()

**Location:** `api/auth_api.py`

**Behavior:**

1. Read `Authorization: Bearer <token>`.
2. If no/invalid header and `ALLOW_ANONYMOUS_DEV=1`, return synthetic dev user (local only).
3. Otherwise:
   - **API key:** If token starts with `ak_live_`, validate via `api_keys` (hash lookup), update `last_used_at`, return user (with `is_admin`, `status`). Invalid/revoked → 401.
   - **JWT:** Decode with HS256; load user by `user_id`; check `status == 'active'`; return user. Invalid/expired → 401 + log.
   - **Session:** If not API key and not valid JWT, treat as legacy session token; validate via `sessions` table and return user. Invalid/expired → 401.

**Returned user dict:** `id`, `email`, `name`, `created_at`, `is_admin`, `status`.

---

## 5. Project Membership

**Table:** `project_members`  
**Roles:** `owner`, `member`, `viewer`

- **owner:** Manage project and members.  
- **member:** Run agents, create/edit workflows.  
- **viewer:** Read-only (results, logs).

**Resolution:** For a given `(project_id, user_id)`:

1. If there is a row in `project_members`, that **role** is used.
2. Else, project’s **team** is used: team owner/admin → project **owner**, team member → **member**.  
So existing teams/projects keep working without backfilling `project_members`.

**On project creation:** The creating user is added as **owner** in `project_members` (see `database/projects.py`).

**Module:** `database/project_members.py` (get_project_role, add/list/update/remove members).

---

## 6. Project Context Validation

**Dependency:** `require_project_context` (in `api/deps.py`)

**Steps:**

1. Read `X-Project-ID` header (or `project_id` query).
2. Resolve user via `get_current_user`.
3. Check access: `user_can_access_project(project_id, user_id)` (uses `get_project_role` / team fallback).
4. If denied → 403 and log **unauthorized_project_access**.
5. Return `{"user": user, "project_id": project_id, "role": "owner"|"member"|"viewer"}`.

**Dependency:** `require_project_can_run`  
Same as above but requires `role in ("owner", "member")`. Used for **/agent/run** so **viewers** get 403 when trying to run agents.

---

## 7. API Key System

**Table:** `api_keys`  
**Format:** Plain key = `ak_live_` + random part; only **hash** is stored.

**Endpoints:**

- **POST /api-keys** – Body: `{ "name": "..." }`. Creates key; returns `id`, **key** (plain), `name`, `created_at`. Plain key is shown only once.
- **GET /api-keys** – List current user’s keys (id, name, created_at, last_used_at); no plain key.
- **DELETE /api-keys/{id}** – Revoke key; only owner can delete.

**Authentication:** Client sends `Authorization: Bearer ak_live_xxxxxxxxx`. Resolved in `get_current_user` before JWT/session.

---

## 8. Admin Permissions

**Dependency:** `require_admin` (in `api/deps.py`)

**Rule:** `user.get("is_admin")` must be `True` (from DB). No env-based admin list.

**Used on:** All **/system/*** routes (metrics, workers, queue, containers, recovery, autoscaler, dead_letters, alerts, health).  
Other admin-only paths (e.g. **/workers/***, **/metrics/***, **/alerts/***) can be protected the same way by adding `Depends(require_admin)`.

---

## 9. Secure Endpoints (Summary)

| Area            | Protection                          |
|-----------------|-------------------------------------|
| /agent/run      | `require_project_can_run` (owner/member) |
| /task/*, /tasks/* | `require_project_context` + task project check |
| /workflows/*    | `require_project_context` (existing) |
| /installations/* | `require_project_context` (existing) |
| /events/*       | `require_project_context` (existing) |
| /dashboard      | `require_project_context` (existing) |
| /system/*       | `require_admin`                     |
| /api-keys       | `get_current_user`                  |
| /auth/login     | Rate limited (10/min)               |
| /auth/register  | Public (password rules enforced)    |

---

## 10. Rate Limiting

**Middleware:** `api/rate_limit.py` (in-memory, per client IP or `X-Forwarded-For`).

| Path / pattern   | Limit (per minute) |
|------------------|---------------------|
| /auth/login      | 10                  |
| /agent/run       | 20                  |
| /webhooks/*      | 60                  |
| General API      | 100                 |

**Response when exceeded:** HTTP **429** with `Retry-After` and body `{"detail": "Too many requests", "retry_after": 60}`.  
**Logging:** **rate_limit_exceeded** (client key, path, limit, window).

---

## 11. Password Security

- **Minimum length:** 8 characters (enforced in register).
- **Storage:** SHA-256 hashes.
- **Optional complexity:** If `PASSWORD_REQUIRE_COMPLEXITY=1`, require at least one uppercase letter, one number, and one symbol (regex in `auth_api._validate_password`).

---

## 12. Security Headers

**Middleware:** `SecurityHeadersMiddleware` in `api/main.py` (runs for all responses).

- **X-Content-Type-Options:** `nosniff`
- **X-Frame-Options:** `DENY`
- **X-XSS-Protection:** `1; mode=block`

---

## 13. Logging

**Logger:** `security` (in `api/security_logger.py`).

**Events:**

- **failed_login** – Invalid credentials or inactive account on login (email, reason, client, path).
- **invalid_jwt** – Invalid or expired JWT (reason, client, path).
- **unauthorized_access** – 401/403 (detail, path, client, status_code).
- **unauthorized_project_access** – 403 when user not in project (user_id, project_id, client, path).
- **rate_limit_exceeded** – 429 (client_key, path, limit, window).

Use the `security` logger in your logging config (e.g. file or SIEM); optional `SECURITY_LOG_JSON=1` for JSON-style output.

---

## 14. Environment Variables

| Variable                     | Purpose |
|-----------------------------|---------|
| JWT_SECRET                  | HS256 signing secret; **required** in production. |
| ALLOW_ANONYMOUS_DEV         | If 1/true/yes, bypass auth (dev only). |
| PASSWORD_REQUIRE_COMPLEXITY | If 1/true/yes, enforce uppercase + number + symbol. |
| SECURITY_LOG_JSON           | Optional; emit security log as JSON. |

---

## 15. Modified / New Files

| File | Purpose |
|------|---------|
| database/migrations.py | Schema: users is_admin/status, project_members, api_keys. |
| database/users.py | SHA-256 password hashes; minimal user CRUD. |
| database/project_members.py | project_members CRUD and get_project_role. |
| database/api_keys.py | API key create/list/delete and get_user_by_key. |
| database/projects.py | user_can_access_project via get_project_role; add owner to project_members on create. |
| api/auth_api.py | JWT create/decode; get_current_user (API key → JWT → session); password validation; failed login log. |
| api/deps.py | require_project_context (returns role), require_project_can_run, require_admin (DB is_admin). |
| api/api_keys_api.py | POST/GET/DELETE /api-keys. |
| api/security_logger.py | log_failed_login, log_invalid_jwt, log_unauthorized_project_access. |
| api/rate_limit.py | /auth/login 10/min. |
| api/main.py | run_migrations; SecurityHeadersMiddleware; api_keys_router; require_project_can_run on /agent/run. |

---

All existing platform functionality (teams, projects, workflows, installations, events, dashboard, system endpoints) remains operational; auth and project context are enforced with the same theme (Bearer token, X-Project-ID, 401/403/429 and logging).
