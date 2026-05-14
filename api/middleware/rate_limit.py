"""
Redis-based rate limiting for authentication endpoints.

- /auth/login: 5 attempts per minute per IP
- /auth/forgot-password: 5 attempts per minute per IP (per-email 3/hour enforced in endpoint)
- /auth/reset-password: 5 attempts per minute per IP
- /auth/google/login: 5 attempts per minute per IP

Returns HTTP 429 when limit exceeded.
"""

from __future__ import annotations

import os
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
AUTH_RATE_LIMIT_KEY_PREFIX = "auth_rl:"

# path prefix -> (max attempts, window seconds)
RULES = [
    ("/auth/login", 5, 60),
    ("/auth/forgot-password", 5, 60),
    ("/auth/reset-password", 5, 60),
]


def _get_redis():
    try:
        import redis
        return redis.from_url(REDIS_URL, decode_responses=True)
    except Exception:
        return None


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _path_matches(path: str) -> tuple[int, int] | None:
    for prefix, limit, window in RULES:
        if path == prefix or path.startswith(prefix + "/") or path.startswith(prefix.rstrip("/") + "/"):
            return (limit, window)
    return None


def check_auth_rate_limit(request: Request) -> tuple[bool, int]:
    """
    Check Redis-based auth rate limit. Returns (allowed, retry_after_seconds).
    If Redis unavailable, allow request (fail open for availability).
    """
    path = (request.url.path or "").strip()
    rule = _path_matches(path)
    if not rule:
        return (True, 0)
    limit, window = rule
    ip = _client_ip(request)
    key = f"{AUTH_RATE_LIMIT_KEY_PREFIX}ip:{path}:{ip}"
    r = _get_redis()
    if not r:
        return (True, 0)
    try:
        pipe = r.pipeline()
        pipe.incr(key)
        pipe.ttl(key)
        results = pipe.execute()
        count = results[0]
        ttl = results[1]
        if ttl == -1:
            r.expire(key, window)
            ttl = window
        if count > limit:
            return (False, ttl if ttl > 0 else window)
        return (True, 0)
    except Exception:
        return (True, 0)


def check_forgot_password_rate_limit_by_email(email: str) -> tuple[bool, int]:
    """
    Check 3 forgot-password requests per hour per email. Returns (allowed, retry_after_seconds).
    """
    email_key = (email or "").strip().lower()
    if not email_key:
        return (True, 0)
    key = f"{AUTH_RATE_LIMIT_KEY_PREFIX}forgot_email:{email_key}"
    r = _get_redis()
    if not r:
        return (True, 0)
    window = 3600  # 1 hour
    limit = 3
    try:
        pipe = r.pipeline()
        pipe.incr(key)
        pipe.ttl(key)
        results = pipe.execute()
        count = results[0]
        ttl = results[1]
        if ttl == -1:
            r.expire(key, window)
            ttl = window
        if count > limit:
            return (False, ttl if ttl > 0 else window)
        return (True, 0)
    except Exception:
        return (True, 0)


class AuthRateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware: apply Redis rate limits to auth endpoints."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = (request.url.path or "").strip()
        if path.startswith("/docs") or path.startswith("/redoc") or path.startswith("/openapi"):
            return await call_next(request)
        if not _path_matches(path):
            return await call_next(request)
        allowed, retry_after = check_auth_rate_limit(request)
        if not allowed:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many attempts. Try again later."},
                headers={"Retry-After": str(retry_after)},
            )
        return await call_next(request)
