"""Workflow routes — delegate to legacy `api.workflow_api` until migrated."""

from __future__ import annotations

from fastapi import APIRouter

from api.workflow_api import router as legacy_workflow  # noqa: E402

router = APIRouter()
router.include_router(legacy_workflow)
