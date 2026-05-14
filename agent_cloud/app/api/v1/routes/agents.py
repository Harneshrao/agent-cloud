"""Agent marketplace routes — delegate to legacy routers."""

from __future__ import annotations

from fastapi import APIRouter

from api.agent_store_api import router as store_router  # noqa: E402

router = APIRouter()
router.include_router(store_router)
