"""Auth routes — delegate to legacy `api.auth_api` until migrated."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()

# Mount legacy auth router for compatibility (token URLs unchanged).
from api.auth_api import router as legacy_auth  # noqa: E402

router.include_router(legacy_auth)
