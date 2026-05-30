"""
Plan limit definitions — extends DB plan rows with operational caps.

DB `plans` holds monthly_run_limit and monthly_execution_time_limit_ms.
Additional caps are defined here by plan name until migrated to JSON on plans.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from database.plans import get_plan_by_name
from database.project_plans import get_current_plan_for_project

# Defaults merged with DB plan row
_EXTRA_LIMITS: Dict[str, Dict[str, Any]] = {
    "Free": {
        "max_deployments": 5,
        "max_artifact_storage_mb": 100,
        "max_concurrent_running": 3,
        "max_api_requests_per_minute": 60,
        "max_retries_per_hour": 50,
        "max_artifact_upload_mb": 10,
        "max_queue_depth_warn": 200,
    },
    "Starter": {
        "max_deployments": 25,
        "max_artifact_storage_mb": 1024,
        "max_concurrent_running": 10,
        "max_api_requests_per_minute": 300,
        "max_retries_per_hour": 500,
        "max_artifact_upload_mb": 10,
        "max_queue_depth_warn": 2000,
    },
    "Growth": {
        "max_deployments": 100,
        "max_artifact_storage_mb": 10240,
        "max_concurrent_running": 50,
        "max_api_requests_per_minute": 1200,
        "max_retries_per_hour": 5000,
        "max_artifact_upload_mb": 25,
        "max_queue_depth_warn": 20000,
    },
}


def get_limits_for_project(project_id) -> Dict[str, Any]:
    import uuid

    pid = project_id if isinstance(project_id, uuid.UUID) else uuid.UUID(str(project_id))
    plan = get_current_plan_for_project(pid)
    if plan is None:
        plan = get_plan_by_name("Free")
    name = (plan or {}).get("name") or "Free"
    extra = dict(_EXTRA_LIMITS.get(name, _EXTRA_LIMITS["Free"]))
    if plan:
        extra["plan_id"] = plan["id"]
        extra["plan_name"] = plan["name"]
        extra["monthly_run_limit"] = plan.get("monthly_run_limit")
        extra["monthly_execution_time_limit_ms"] = plan.get(
            "monthly_execution_time_limit_ms"
        )
        extra["price_usd"] = plan.get("price_usd")
    else:
        extra["plan_name"] = "Free"
        extra["monthly_run_limit"] = 1000
        extra["monthly_execution_time_limit_ms"] = 600_000
        extra["price_usd"] = 0.0
    return extra
