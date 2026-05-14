"""
Quota checker: enforce subscription plan limits before enqueuing tasks.

Uses usage_records for runs_this_month and execution_time_this_month,
and project_plans + plans for limits. Raises QuotaExceeded for 429 responses.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict

from database.plans import get_plan_by_name
from database.project_plans import get_current_plan_for_project
from database.usage_records import get_usage_this_month


class QuotaExceeded(Exception):
    """Raised when project has exceeded its usage limits. API should return 429."""

    pass


def check_quota(project_id: uuid.UUID) -> None:
    """
    Check if the project is within its monthly run and execution-time limits.
    If exceeded, raises QuotaExceeded so the API can return 429 with
    {"error": "usage_quota_exceeded"}.
    """
    summary = get_usage_summary(project_id)
    runs_used = summary["runs_used"]
    runs_limit = summary["runs_limit"]
    execution_time_used = summary["execution_time_used"]
    execution_time_limit = summary["execution_time_limit"]

    if runs_limit is not None and runs_used >= runs_limit:
        raise QuotaExceeded("Monthly run limit exceeded")
    if execution_time_limit is not None and execution_time_used >= execution_time_limit:
        raise QuotaExceeded("Monthly execution time limit exceeded")


def get_usage_summary(project_id: uuid.UUID) -> Dict[str, Any]:
    """
    Return usage summary for the dashboard: runs_used, runs_limit,
    execution_time_used, execution_time_limit.
    If project has no plan, use Free plan limits for display.
    """
    usage = get_usage_this_month(project_id)
    runs_used = usage["runs_this_month"]
    execution_time_used = usage["execution_time_this_month_ms"]

    plan = get_current_plan_for_project(project_id)
    if plan is None:
        free = get_plan_by_name("Free")
        if free is not None:
            plan = free
    if plan is None:
        return {
            "runs_used": runs_used,
            "runs_limit": None,
            "execution_time_used": execution_time_used,
            "execution_time_limit": None,
        }
    return {
        "runs_used": runs_used,
        "runs_limit": plan["monthly_run_limit"],
        "execution_time_used": execution_time_used,
        "execution_time_limit": plan["monthly_execution_time_limit_ms"],
    }
