"""
Distributed API rate limiting (Redis sliding window).

Keys (namespace `api_rl:v1:`):
  user:{sub}:{path_bucket} — from Bearer JWT `sub` when present
  proj:{project_uuid}:{path_bucket} — when X-Project-ID is a valid UUID
  ip:{client_ip}:{path_bucket} — fallback identity

A request must pass all applicable limits (user or ip, plus project when scoped).

429 Too Many Requests when exceeded. Fails open if Redis is unavailable (availability).
"""

from __future__ import annotations

import os
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from api.security_logger import log_rate_limit_exceeded
from config.settings import REDIS_URL

RULES = [
    ("/agent/run", 20, 60),
    ("/agents/run", 20, 60),
    ("/webhooks/", 60, 60),
]
DEFAULT_LIMIT = 100
DEFAULT_WINDOW = 60

_SLIDING_LUA = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local member = ARGV[4]
redis.call('ZREMRANGEBYSCORE', key, '-inf', now - window)
local cnt = redis.call('ZCARD', key)
if tonumber(cnt) >= tonumber(limit) then
  return 0
end
redis.call('ZADD', key, now, member)
redis.call('EXPIRE', key, window + 2)
return 1
"""

_redis = None


def _client():
    global _redis
    if _redis is not None:
        return _redis
    try:
        import redis as redis_lib

        _redis = redis_lib.from_url(REDIS_URL, decode_responses=True)
    except Exception:
        return None
    return _redis


def _path_rule(path: str) -> tuple[int, int]:
    for prefix, limit, window in RULES:
        if path.startswith(prefix) or path == prefix.rstrip("/"):
            return (limit, window)
    return (DEFAULT_LIMIT, DEFAULT_WINDOW)


def _path_bucket(path: str) -> str:
    for prefix, _, _ in RULES:
        if path.startswith(prefix):
            return prefix[:48]
    return "general"


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _bearer_sub(request: Request) -> str | None:
    auth = request.headers.get("Authorization") or ""
    if not auth.lower().startswith("bearer "):
        return None
    token = auth[7:].strip()
    if not token:
        return None
    try:
        from jose import jwt

        claims = jwt.get_unverified_claims(token)
        sub = claims.get("sub")
        if sub:
            return str(sub)[:128]
    except Exception:
        return None
    return None


def _project_uuid_header(request: Request) -> str | None:
    raw = request.headers.get("X-Project-ID") or request.query_params.get("project_id")
    if not raw or not str(raw).strip():
        return None
    s = str(raw).strip()
    try:
        import uuid as u

        return str(u.UUID(s))
    except ValueError:
        return None


def _sliding_allow(r, key: str, limit: int, window: int) -> bool:
    now = time.time()
    member = f"{now}:{uuid.uuid4().hex}"
    try:
        ok = r.eval(_SLIDING_LUA, 1, key, str(now), str(window), str(limit), member)
        return int(ok) == 1
    except Exception:
        return True


def _check_limits(request: Request, path: str) -> tuple[bool, int, int]:
    limit, window = _path_rule(path)
    bucket = _path_bucket(path)
    r = _client()
    if not r:
        return (True, limit, window)

    ip = _client_ip(request)
    sub = _bearer_sub(request)
    proj = _project_uuid_header(request)

    checks: list[tuple[str, str]] = []
    if sub:
        checks.append((f"api_rl:v1:user:{sub}:{bucket}", "user"))
    else:
        checks.append((f"api_rl:v1:ip:{ip}:{bucket}", "ip"))
    if proj:
        checks.append((f"api_rl:v1:proj:{proj}:{bucket}", "proj"))

    for key, _kind in checks:
        if not _sliding_allow(r, key, limit, window):
            return (False, limit, window)
    return (True, limit, window)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis sliding-window rate limits by user/project/IP and path bucket."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if os.environ.get("ALLOW_ANONYMOUS_DEV", "").strip().lower() in ("1", "true", "yes"):
            return await call_next(request)
        path = request.url.path or ""
        if path.startswith("/docs") or path.startswith("/redoc") or path.startswith("/openapi"):
            return await call_next(request)
        if path == "/health":
            return await call_next(request)
        if path == "/dashboard":
            return await call_next(request)

        allowed, limit, window = _check_limits(request, path)
        if not allowed:
            ip = _client_ip(request)
            log_rate_limit_exceeded(ip, path, limit, window)
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests", "retry_after": window},
                headers={"Retry-After": str(window)},
            )
        return await call_next(request)
