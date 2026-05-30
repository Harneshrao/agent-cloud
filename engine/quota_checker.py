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
    Check if the project is within plan limits before enqueue/run.
    Delegates to services.quota_service (runs, time, concurrency).
    """
    from services.quota_service import check_enqueue_quota

    check_enqueue_quota(project_id)


def get_usage_summary(project_id: uuid.UUID) -> Dict[str, Any]:
    """Dashboard-compatible summary (legacy keys + billing summary)."""
    from services.quota_service import get_billing_summary

    bill = get_billing_summary(project_id)
    u = bill["usage"]
    lim = bill["limits"]
    return {
        "runs_used": u["runs_enqueued"],
        "runs_limit": lim.get("monthly_run_limit"),
        "execution_time_used": u["execution_time_ms"],
        "execution_time_limit": lim.get("monthly_execution_time_limit_ms"),
        "billing": bill,
    }
