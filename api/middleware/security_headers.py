"""
Security headers middleware.

Adds security headers only for non-docs routes. /docs, /redoc, and /openapi.json
bypass immediately so their responses are never touched (Swagger UI and ReDoc load).
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


def _is_docs_path(path: str) -> bool:
    if not path:
        return False
    p = path.strip().rstrip("/")
    return (
        p == "/docs"
        or p.startswith("/docs/")
        or p == "/redoc"
        or p.startswith("/redoc/")
        or p == "/openapi.json"
        or p.startswith("/openapi")
    )


API_CSP = (
    "default-src 'self' https: data: blob: 'unsafe-inline' 'unsafe-eval'; "
    "img-src 'self' data: https:; "
    "script-src 'self' https: 'unsafe-inline' 'unsafe-eval'; "
    "style-src 'self' https: 'unsafe-inline';"
)
HSTS_VALUE = "max-age=31536000; includeSubDomains; preload"


def _is_secure(request: Request) -> bool:
    if request.url.scheme != "https":
        return False
    host = request.url.hostname or ""
    if host in ("localhost", "127.0.0.1"):
        return False
    if request.headers.get("X-Forwarded-Proto") == "https":
        return True
    return True


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers only for non-docs. Docs paths return immediately
    without any header so Swagger UI / ReDoc work.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.scope.get("path") or request.url.path or ""
        if _is_docs_path(path):
            return await call_next(request)

        response = await call_next(request)
        response.headers["x-content-type-options"] = "nosniff"
        response.headers["x-frame-options"] = "DENY"
        response.headers["x-xss-protection"] = "1; mode=block"
        response.headers["Content-Security-Policy"] = API_CSP
        if _is_secure(request):
            response.headers["Strict-Transport-Security"] = HSTS_VALUE
        return response
