"""
FastAPI application factory (`agent_cloud` modular layout).

Mount legacy routers during migration, or switch traffic to `v1` only after cutover.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from agent_cloud.app.api.v1.router import router as v1_router


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    if os.environ.get("SKIP_MIGRATION_CHECK", "").strip().lower() not in (
        "1",
        "true",
        "yes",
    ):
        from api.migration_check import assert_migrations_applied

        assert_migrations_applied()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Agent Cloud",
        version="2.0.0",
        lifespan=_lifespan,
    )
    app.include_router(v1_router, prefix="/v1")
    app.add_api_route("/health", lambda: {"status": "ok"}, methods=["GET"])
    return app


app = create_app()
