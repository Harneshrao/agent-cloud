"""
FastAPI application factory (`agent_cloud` package entrypoint).

Returns the same ASGI application as `api.main:app` (includes `/v1` modular routes).
"""

from __future__ import annotations

from fastapi import FastAPI


def create_app() -> FastAPI:
    """Single ASGI graph: reuse the hardened legacy app (includes `/v1` modular routes)."""
    from api.main import app as legacy_app

    return legacy_app


app = create_app()
