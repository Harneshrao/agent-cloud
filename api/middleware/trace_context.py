"""Propagate X-Request-ID / X-Trace-ID into observability context for structured logs."""

from __future__ import annotations

import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from agent_cloud.infra.observability.context import reset_trace_id, set_trace_id


class TraceContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        raw = (
            request.headers.get("X-Request-ID")
            or request.headers.get("X-Trace-ID")
            or ""
        ).strip()
        tid = raw if raw else str(uuid.uuid4())
        token = set_trace_id(tid)
        try:
            response = await call_next(request)
        finally:
            reset_trace_id(token)
        response.headers["X-Request-ID"] = tid
        return response
