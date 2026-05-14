# Refresh Tokens and Session Management

This document describes the **refresh token and session management** layer added to the auth system: short-lived access tokens (JWT 15 min), long-lived refresh tokens (30 days), token rotation on refresh, logout, and session limits.

---

## 1. Database: refresh_tokens Table

**Migration:** `database/migrations.py` (appended to `run_migrations()`).

**Schema:**

```sql
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token_hash TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    revoked INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

- **token_hash:** SHA-256 hash of the refresh token; raw token is never stored.
- **expires_at:** 30 days from creation.
- **revoked:** 1 = revoked (logout or rotated); 0 = active.
- Indexes: `token_hash` (unique), `user_id`, `expires_at`.

**Module:** `database/refresh_tokens.py` — create_refresh_token, get_by_token, revoke_by_id, revoke_by_token, count_active_per_user. Max 5 active tokens per user; oldest are revoked when creating a new one.

---

## 2. Login Flow (Modified)

**Endpoint:** `POST /auth/login`

**Response (new):**

```json
{
  "user": { "id", "email", "name", "created_at", "is_admin", "status" },
  "access_token": "<JWT>",
  "refresh_token": "<opaque token, store securely>",
  "token_type": "bearer",
  "expires_in_minutes": 15
}
```

- **Access token:** JWT, **15 minutes** expiration, HS256. Use as `Authorization: Bearer <access_token>` for API calls.
- **Refresh token:** Opaque string (e.g. `secrets.token_urlsafe(48)`), **30 days** expiration. Stored as **hash** in `refresh_tokens`. Used only with `POST /auth/refresh` or `POST /auth/logout`; never sent as Bearer for normal API access.

---

## 3. Secure Refresh Token Generation

- **Generate:** `secrets.token_urlsafe(48)` (cryptographically secure).
- **Store:** `hashlib.sha256(token.encode()).hexdigest()` in `refresh_tokens.token_hash`.
- Raw token is returned to the client only once (on login or after refresh); client must store it securely (e.g. httpOnly cookie or secure storage).

---

## 4. Refresh Endpoint

**Endpoint:** `POST /auth/refresh`

**Body:**

```json
{ "refresh_token": "..." }
```

**Steps:**

1. Hash the provided token and look up in `refresh_tokens`.
2. Verify row exists, `revoked = 0`, and `expires_at > now`.
3. **Rate limit:** 10 requests per minute per user (in-memory); if exceeded → **429**.
4. Load user; if missing or inactive → **401**.
5. **Rotation:** Revoke the old refresh token (`revoked = 1`), create a new refresh token (and enforce max 5 per user).
6. Issue new JWT access token (15 min).
7. Return new `access_token` and `refresh_token`; client should replace stored refresh token with the new one.

**Response:** Same shape as login (access_token, refresh_token, token_type, expires_in_minutes). Old refresh token cannot be used again.

---

## 5. Token Rotation

On every successful `POST /auth/refresh`:

1. **Revoke** the refresh token that was presented.
2. **Generate** a new refresh token and store its hash.
3. **Return** the new refresh token (and new access token) to the client.

This prevents **refresh token replay**: a stolen refresh token can only be used once; the legitimate client gets the new token and the stolen one is invalidated.

---

## 6. Logout Endpoint

**Endpoint:** `POST /auth/logout`

**Body:**

```json
{ "refresh_token": "..." }
```

**Behavior:**

- Look up the refresh token by hash; if found, set `revoked = 1`.
- Log **refresh_token_revoked** (reason: logout) and **logout_event**.
- Always return **200** with `{"status": "logged_out"}` (idempotent; no error if token already invalid/revoked).

The client should discard the stored refresh token and access token after logout.

---

## 7. get_current_user() and Access-Only JWT

- **Bearer token** is interpreted as:
  1. **API key** (prefix `ak_live_`) → resolve via api_keys.
  2. **JWT** → decode and validate (including **exp**); if expired, decode fails → **401**.
  3. **Legacy session** token → resolve via sessions table.

- **Refresh tokens are not accepted** as Bearer for API calls. They are not looked up in get_current_user. If a client sends an expired JWT, the response is **401** with a message that the client should call `POST /auth/refresh` to get a new access token.

---

## 8. Session Limits

- **Max 5 active refresh tokens per user.** “Active” = not revoked and not expired.
- When creating a new refresh token (login or refresh), if the user already has 5 active tokens, the **oldest** (by `created_at`) are revoked until only 4 remain, then the new one is added (total 5).
- Implemented in `database/refresh_tokens.create_refresh_token()`.

---

## 9. Security Logging

**Logger:** `security` (see `api/security_logger.py`).

**Events:**

| Event | When |
|-------|------|
| **refresh_token_used** | A refresh token was successfully used (before rotation). |
| **refresh_token_revoked** | A refresh token was revoked (rotation or logout). |
| **invalid_refresh_attempt** | Invalid, expired, or revoked refresh token was submitted. |
| **logout_event** | User called logout (refresh token revoked). |

All include relevant context (e.g. user_id, reason, client_host, path) in the log extra fields.

---

## 10. Rate Limit on Refresh

- **Limit:** 10 refresh requests per minute **per user**.
- Implemented **inside** `POST /auth/refresh`: after validating the refresh token we have `user_id`; then we check an in-memory per-user sliding window. If the user has already made 10 requests in the last 60 seconds → **429**.
- Stored in `api/auth_api._refresh_attempts` (user_id → list of timestamps). No persistent storage required for this limit.

---

## 11. Security Requirements (Met)

- **Refresh tokens stored as hashes** — only `token_hash` (SHA-256) is stored; raw token never persisted.
- **Secure randomness** — `secrets.token_urlsafe(48)` for refresh tokens; JWT signed with HS256 and secret.
- **Expired tokens rejected** — `get_by_token` checks `expires_at`; JWT decode checks `exp`.
- **Revoked tokens unusable** — `get_by_token` returns None if `revoked = 1`; after rotation or logout the old token is revoked.

---

## 12. Modified and New Files

| File | Change |
|------|--------|
| **database/migrations.py** | Add `refresh_tokens` table and indexes. |
| **database/refresh_tokens.py** | **New.** Create/get/revoke refresh tokens; max 5 per user; 30-day expiry. |
| **api/auth_api.py** | JWT 15 min; login returns access_token + refresh_token; add RefreshRequest/LogoutRequest; POST /auth/refresh (rotation + rate limit); POST /auth/logout; get_current_user doc updated. |
| **api/security_logger.py** | log_refresh_token_used, log_refresh_token_revoked, log_invalid_refresh_attempt, log_logout_event. |
| **REFRESH_TOKENS_AND_SESSIONS.md** | **New.** This document. |

---

## 13. Client Usage

1. **Login:** `POST /auth/login` → store `access_token` (e.g. in memory or short-lived storage) and `refresh_token` (e.g. httpOnly cookie or secure storage). Use `access_token` as `Authorization: Bearer <access_token>`.
2. **API call returns 401:** If the response indicates expired/invalid token, call `POST /auth/refresh` with `{"refresh_token": "..."}` → receive new `access_token` and `refresh_token`; replace stored tokens and retry the request.
3. **Logout:** `POST /auth/logout` with `{"refresh_token": "..."}` → discard both tokens on the client.

This yields short-lived access tokens and secure, revocable sessions suitable for production SaaS.
