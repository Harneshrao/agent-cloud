"""
Quota enforcement — single gate before billable actions.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from agent_runtime.storage_paths import get_storage_root
from database import usage_events as usage_db
from database.usage_records import get_usage_this_month
from engine.quota_checker import QuotaExceeded  # re-export
from services.plan_limits import get_limits_for_project

__all__ = ["QuotaExceeded", "check_enqueue_quota", "check_deployment_quota", "check_artifact_upload", "check_retry_allowed", "get_billing_summary"]


def _artifact_storage_bytes(project_id: uuid.UUID) -> int:
    root = get_storage_root() / "projects" / str(project_id) / "artifacts"
    if not root.exists():
        return 0
    total = 0
    for p in root.rglob("*.zip"):
        try:
            total += p.stat().st_size
        except OSError:
            pass
    return total


def get_billing_summary(project_id: uuid.UUID) -> Dict[str, Any]:
    """Unified usage + limits for dashboard."""
    limits = get_limits_for_project(project_id)
    legacy = get_usage_this_month(project_id)
    breakdown = usage_db.usage_breakdown_month(project_id)
    storage_bytes = _artifact_storage_bytes(project_id)
    running = usage_db.count_running_tasks(project_id)

    from database import deployment_store

    deployments = len(deployment_store.list_deployments(project_id))

    runs_used = int(breakdown.get("tasks_enqueued") or legacy["runs_this_month"])
    exec_used = int(
        breakdown.get("execution_time_ms") or legacy["execution_time_this_month_ms"]
    )

    return {
        "project_id": str(project_id),
        "plan": {
            "name": limits.get("plan_name"),
            "price_usd": limits.get("price_usd"),
        },
        "usage": {
            "runs_enqueued": runs_used,
            "runs_completed": int(breakdown.get("tasks_completed", 0)),
            "runs_failed": int(breakdown.get("tasks_failed", 0)),
            "retries": int(breakdown.get("retries", 0)),
            "dlq_entries": int(breakdown.get("dlq_entries", 0)),
            "execution_time_ms": exec_used,
            "deployments": deployments,
            "artifact_storage_mb": round(storage_bytes / (1024 * 1024), 2),
            "concurrent_running": running,
            "legacy_runs_this_month": legacy["runs_this_month"],
        },
        "limits": {
            "monthly_run_limit": limits.get("monthly_run_limit"),
            "monthly_execution_time_limit_ms": limits.get(
                "monthly_execution_time_limit_ms"
            ),
            "max_deployments": limits.get("max_deployments"),
            "max_artifact_storage_mb": limits.get("max_artifact_storage_mb"),
            "max_concurrent_running": limits.get("max_concurrent_running"),
            "max_retries_per_hour": limits.get("max_retries_per_hour"),
            "max_artifact_upload_mb": limits.get("max_artifact_upload_mb"),
            "max_api_requests_per_minute": limits.get("max_api_requests_per_minute"),
        },
        "warnings": _usage_warnings(
            runs_used,
            exec_used,
            running,
            deployments,
            storage_bytes,
            limits,
            project_id,
        ),
    }


def _usage_warnings(
    runs_used: int,
    exec_used: int,
    running: int,
    deployments: int,
    storage_bytes: int,
    limits: Dict[str, Any],
    project_id: uuid.UUID,
) -> list[Dict[str, str]]:
    warnings: list[Dict[str, str]] = []
    run_lim = limits.get("monthly_run_limit")
    if run_lim is not None and runs_used >= 0.9 * run_lim:
        warnings.append(
            {
                "code": "runs_near_limit",
                "message": f"Monthly runs at {runs_used}/{run_lim}",
            }
        )
    time_lim = limits.get("monthly_execution_time_limit_ms")
    if time_lim is not None and exec_used >= 0.9 * time_lim:
        warnings.append(
            {
                "code": "execution_time_near_limit",
                "message": f"Execution time nearing monthly cap",
            }
        )
    max_dep = limits.get("max_deployments")
    if max_dep is not None and deployments >= max_dep:
        warnings.append(
            {"code": "deployments_at_limit", "message": "Deployment count at plan limit"}
        )
    max_st = limits.get("max_artifact_storage_mb")
    if max_st is not None and storage_bytes >= max_st * 1024 * 1024 * 0.9:
        warnings.append(
            {"code": "storage_near_limit", "message": "Artifact storage nearing cap"}
        )
    if usage_db.retries_last_hour(project_id) >= 0.8 * limits.get(
        "max_retries_per_hour", 50
    ):
        warnings.append(
            {"code": "retry_storm_risk", "message": "High retry rate in the last hour"}
        )
    return warnings


def check_enqueue_quota(project_id: uuid.UUID) -> None:
    """Before enqueue: runs, execution budget, concurrent cap."""
    limits = get_limits_for_project(project_id)
    legacy = get_usage_this_month(project_id)
    breakdown = usage_db.usage_breakdown_month(project_id)
    runs_used = int(breakdown.get("tasks_enqueued") or legacy["runs_this_month"])
    exec_used = int(
        breakdown.get("execution_time_ms") or legacy["execution_time_this_month_ms"]
    )

    run_lim = limits.get("monthly_run_limit")
    if run_lim is not None and runs_used >= run_lim:
        raise QuotaExceeded("Monthly task execution limit exceeded")

    time_lim = limits.get("monthly_execution_time_limit_ms")
    if time_lim is not None and exec_used >= time_lim:
        raise QuotaExceeded("Monthly execution time limit exceeded")

    max_conc = limits.get("max_concurrent_running")
    if max_conc is not None:
        running = usage_db.count_running_tasks(project_id)
        if running >= max_conc:
            raise QuotaExceeded(
                f"Concurrent run limit exceeded ({running}/{max_conc})"
            )


def check_deployment_quota(project_id: uuid.UUID) -> None:
    limits = get_limits_for_project(project_id)
    max_dep = limits.get("max_deployments")
    if max_dep is None:
        return
    from database import deployment_store

    n = len(deployment_store.list_deployments(project_id))
    if n >= max_dep:
        raise QuotaExceeded("Deployment count limit exceeded for plan")


def check_artifact_upload(project_id: uuid.UUID, upload_bytes: int) -> None:
    limits = get_limits_for_project(project_id)
    max_mb = limits.get("max_artifact_upload_mb", 10)
    if upload_bytes > max_mb * 1024 * 1024:
        raise QuotaExceeded(f"Artifact exceeds max upload size ({max_mb} MB)")

    max_storage = limits.get("max_artifact_storage_mb")
    if max_storage is not None:
        current = _artifact_storage_bytes(project_id)
        if current + upload_bytes > max_storage * 1024 * 1024:
            raise QuotaExceeded("Project artifact storage limit exceeded")


def check_retry_allowed(project_id: uuid.UUID) -> None:
    limits = get_limits_for_project(project_id)
    max_r = limits.get("max_retries_per_hour", 50)
    if usage_db.retries_last_hour(project_id) >= max_r:
        raise QuotaExceeded("Retry rate limit exceeded (retry storm protection)")
