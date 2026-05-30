"""
Billing and usage API — project-scoped limits, ledger, and warnings.
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query

from api.deps import require_project_context
from database import usage_events as usage_db
from database.usage_records import get_aggregated
from services.quota_service import get_billing_summary

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/summary")
def billing_summary(context: dict = Depends(require_project_context)):
    """Unified usage + limits + warnings for the dashboard."""
    project_id = context["project_id"]
    return get_billing_summary(project_id)


@router.get("/limits")
def billing_limits(context: dict = Depends(require_project_context)):
    """Plan limits only."""
    bill = get_billing_summary(context["project_id"])
    return {"plan": bill["plan"], "limits": bill["limits"], "warnings": bill["warnings"]}


@router.get("/events")
def billing_events(
    limit: int = Query(100, ge=1, le=500),
    event_type: Optional[str] = None,
    context: dict = Depends(require_project_context),
):
    project_id = context["project_id"]
    return {
        "events": usage_db.list_usage_events(
            project_id, limit=limit, event_type=event_type
        )
    }


@router.get("/usage")
def billing_usage_legacy(
    start_date: str | None = None,
    end_date: str | None = None,
    context: dict = Depends(require_project_context),
):
    """Aggregated usage_records + billing summary (compat with GET /usage)."""
    project_id = context["project_id"]
    data = get_aggregated(project_id, start_date=start_date, end_date=end_date)
    bill = get_billing_summary(project_id)
    return {
        "project_id": str(project_id),
        "total_runs": data["total_runs"],
        "total_execution_time_ms": data["total_execution_time_ms"],
        "runs_per_agent": data["runs_per_agent"],
        "usage_per_day": data["usage_per_day"],
        "top_agents": data["top_agents"],
        "billing": bill,
    }
