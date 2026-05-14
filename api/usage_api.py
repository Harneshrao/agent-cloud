"""
Usage API: aggregated usage metrics for billing and dashboards.

GET /usage - Project-scoped usage: total_runs, total_execution_time, runs_per_agent,
            usage_per_day, top_agents. Query params: project_id (via context), start_date, end_date.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from api.deps import require_project_context
from database.usage_records import get_aggregated
from engine.quota_checker import get_usage_summary


router = APIRouter(tags=["usage"])


@router.get("/usage")
def get_usage(
    context: dict = Depends(require_project_context),
    start_date: str | None = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: str | None = Query(None, description="End date (YYYY-MM-DD)"),
):
    """
    Return aggregated usage for the project. Requires Authorization and X-Project-ID (or project_id query).
    Supports agent usage charts, workflow usage per day, and top agents by usage.
    """
    project_id = context["project_id"]
    data = get_aggregated(
        project_id=project_id,
        start_date=start_date,
        end_date=end_date,
    )
    summary = get_usage_summary(project_id)
    return {
        "project_id": project_id,
        "total_runs": data["total_runs"],
        "total_execution_time": data["total_execution_time_ms"],
        "total_execution_time_ms": data["total_execution_time_ms"],
        "runs_per_agent": data["runs_per_agent"],
        "usage_per_day": data["usage_per_day"],
        "top_agents": data["top_agents"],
        "runs_used": summary["runs_used"],
        "runs_limit": summary["runs_limit"],
        "execution_time_used": summary["execution_time_used"],
        "execution_time_limit": summary["execution_time_limit"],
    }
