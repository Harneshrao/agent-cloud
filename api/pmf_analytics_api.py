"""
PMF & activation analytics — event ingestion + founder dashboard API.

POST /analytics/events     — client/server product events (auth optional in dev)
GET  /analytics/pmf/summary — founder-only activation funnel & health score
"""

from __future__ import annotations

import os
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.auth_api import get_current_user, get_current_user_optional
from services.pmf_metrics import get_pmf_summary
from services.product_analytics import track

router = APIRouter(prefix="/analytics", tags=["analytics"])


class ProductEventIn(BaseModel):
    event_name: str = Field(..., min_length=1, max_length=120)
    project_id: Optional[str] = None
    deployment_id: Optional[str] = None
    task_id: Optional[str] = None
    session_id: Optional[str] = None
    onboarding_step: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)


class TrackEventsRequest(BaseModel):
    events: List[ProductEventIn] = Field(..., min_length=1, max_length=50)


def _require_founder(user: Dict[str, Any]) -> Dict[str, Any]:
    if os.environ.get("ENABLE_FOUNDER_ANALYTICS", "").strip().lower() in (
        "1",
        "true",
        "yes",
    ):
        return user
    raw = os.environ.get("FOUNDER_EMAILS", "").strip()
    if raw:
        allowed = {e.strip().lower() for e in raw.split(",") if e.strip()}
        if str(user.get("email", "")).lower() in allowed:
            return user
    if user.get("is_admin"):
        return user
    raise HTTPException(status_code=403, detail="Founder analytics access required")


def _parse_uuid_optional(value: Optional[str]) -> Optional[uuid.UUID]:
    if not value or not str(value).strip():
        return None
    try:
        return uuid.UUID(str(value).strip())
    except ValueError:
        return None


@router.post("/events")
def ingest_events(
    body: TrackEventsRequest,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
):
    """Ingest one or more product analytics events (fire-and-forget)."""
    user_id = user["id"] if user and isinstance(user.get("id"), uuid.UUID) else None
    accepted = 0
    for ev in body.events:
        track(
            ev.event_name.strip(),
            user_id=user_id,
            project_id=_parse_uuid_optional(ev.project_id),
            deployment_id=_parse_uuid_optional(ev.deployment_id),
            task_id=_parse_uuid_optional(ev.task_id),
            session_id=ev.session_id,
            onboarding_step=ev.onboarding_step,
            source="client",
            properties=ev.properties,
        )
        accepted += 1
    return {"accepted": accepted}


@router.get("/pmf/summary")
def pmf_summary(
    days: int = 30,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Founder dashboard: activation funnel, deployment health, trust metrics, PMF score."""
    _require_founder(user)
    days = max(1, min(days, 90))
    return get_pmf_summary(days=days)
