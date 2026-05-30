"""
Per-project token bucket on mutating API routes (X-Project-ID).

Complements user-level TokenBucketRateLimitMiddleware.
"""

from __future__ import annotations

import os
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from agent_cloud.infra.redis.token_bucket import allow, rate_user_key
from config.settings import REDIS_URL
from services.plan_limits import get_limits_for_project


def _project_id_from_request(request: Request) -> str | None:
    raw = request.headers.get("X-Project-ID") or request.query_params.get("project_id")
    if not raw or not str(raw).strip():
        return None
    try:
        return str(uuid.UUID(str(raw).strip()))
    except ValueError:
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


class ProjectRateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limit per project on POST/PATCH/PUT/DELETE when X-Project-ID is set."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if os.environ.get("ENABLE_PROJECT_RATE_LIMIT", "1").strip().lower() in (
            "0",
            "false",
            "no",
        ):
            return await call_next(request)

        path = request.url.path or ""
        if path.startswith("/docs") or path.startswith("/openapi") or path == "/health":
            return await call_next(request)

        if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
            return await call_next(request)

        pid = _project_id_from_request(request)
        if not pid:
            return await call_next(request)

        r = _client()
        if not r:
            return await call_next(request)

        try:
            limits = get_limits_for_project(uuid.UUID(pid))
            cap = float(limits.get("max_api_requests_per_minute", 60))
        except Exception:
            cap = 60.0

        refill = cap / 60.0
        key = rate_user_key(f"project:{pid}")
        if not allow(r, key, capacity=cap, refill_per_sec=refill, cost=1.0):
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Project rate limit exceeded",
                    "limit_type": "project_rate_limit",
                },
            )

        response = await call_next(request)
        try:
            from services.usage_metering import record_api_request

            record_api_request(uuid.UUID(pid), path=path[:200])
        except Exception:
            pass
        return response
