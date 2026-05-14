"""
Token-bucket rate limit at API edge: Redis key `rate:{jwt sub}` when Bearer present.

Complements sliding-window `RateLimitMiddleware`. Enable with ENABLE_TOKEN_BUCKET=1.
"""

from __future__ import annotations

import os
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from agent_cloud.infra.redis.token_bucket import allow, rate_user_key
from config.settings import REDIS_URL


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
            return str(sub)[:256]
    except Exception:
        return None
    return None


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


def _capacity_refill() -> tuple[float, float]:
    cap = float(os.environ.get("TOKEN_BUCKET_CAPACITY", "60"))
    refill = float(os.environ.get("TOKEN_BUCKET_REFILL_PER_SEC", "1.0"))
    return cap, refill


class TokenBucketRateLimitMiddleware(BaseHTTPMiddleware):
    """Per-user token bucket: `rate:{sub}`. Unauthenticated requests skip (use IP middleware elsewhere)."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if os.environ.get("ENABLE_TOKEN_BUCKET", "").strip().lower() not in (
            "1",
            "true",
            "yes",
        ):
            return await call_next(request)
        path = request.url.path or ""
        if path.startswith("/docs") or path.startswith("/redoc") or path.startswith("/openapi"):
            return await call_next(request)
        if path in ("/health", "/dashboard"):
            return await call_next(request)

        sub = _bearer_sub(request)
        if not sub:
            return await call_next(request)

        r = _client()
        if not r:
            return await call_next(request)

        cap, refill = _capacity_refill()
        key = rate_user_key(sub)
        if not allow(r, key, capacity=cap, refill_per_sec=refill, cost=1.0):
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit (token bucket)", "limit_type": "token_bucket"},
            )
        return await call_next(request)
