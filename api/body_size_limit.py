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
MAX_ARTIFACT_UPLOAD_SIZE = 12 * 1024 * 1024  # 12 MB for deployment ZIP uploads


def _max_body_for_path(path: str) -> int:
    if "/deployments/artifacts/upload" in path:
        return MAX_ARTIFACT_UPLOAD_SIZE
    return MAX_BODY_SIZE


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
                limit = _max_body_for_path(path)
                if cl > limit:
                    client = request.client.host if request.client else ""
                    log_request_body_too_large(cl, limit, client_host=client, path=path)
                    return JSONResponse(
                        status_code=413,
                        content={"error": "Request entity too large", "detail": f"Body exceeds {limit} bytes"},
                    )
            except ValueError:
                pass
        response = await call_next(request)
        return response
