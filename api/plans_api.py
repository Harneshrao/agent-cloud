"""
Plans API: list subscription plans and plan details.

GET /plans - Return available subscription plans (id, name, limits, price_usd).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.auth_api import get_current_user
from database.plans import list_plans


router = APIRouter(tags=["plans"])


@router.get("/plans")
def get_plans(user: dict = Depends(get_current_user)):
    """Return available subscription plans. Requires Authorization."""
    plans = list_plans()
    return {"plans": plans}
