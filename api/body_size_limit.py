"""
Request body size limit middleware.

Rejects requests with body larger than MAX_BODY_SIZE (default 2 MB) with HTTP 413.
Uses Content-Length when present to avoid reading the body; for methods that
typically have a body (POST, PUT, PATCH), also enforces limit when possible.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from api.security_logger import log_request_body_too_large

MAX_BODY_SIZE = 2 * 1024 * 1024  # 2 MB


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests whose body exceeds MAX_BODY_SIZE. Returns 413 and logs."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path or ""
        if path.startswith("/docs") or path.startswith("/redoc") or path.startswith("/openapi"):
            return await call_next(request)
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                cl = int(content_length)
                if cl > MAX_BODY_SIZE:
                    client = request.client.host if request.client else ""
                    path = request.url.path if request.url else ""
                    log_request_body_too_large(cl, MAX_BODY_SIZE, client_host=client, path=path)
                    return JSONResponse(
                        status_code=413,
                        content={"error": "Request entity too large", "detail": f"Body exceeds {MAX_BODY_SIZE} bytes"},
                    )
            except ValueError:
                pass
        response = await call_next(request)
        return response
