"""Aggregate v1 routes."""

from __future__ import annotations

from fastapi import APIRouter

from agent_cloud.app.api.v1.routes import agents, auth, system, tasks, workflows

router = APIRouter()
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
# Legacy routers already carry their own prefix (/workflows, /agents, …).
router.include_router(workflows.router, tags=["workflows"])
router.include_router(agents.router, tags=["agents"])
router.include_router(system.router, prefix="/system", tags=["system"])
