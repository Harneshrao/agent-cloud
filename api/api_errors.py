"""
Structured API errors for developer-facing responses.

Every error should answer: what failed, why, what to do next.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def error_detail(
    code: str,
    message: str,
    *,
    hint: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    body: Dict[str, Any] = {
        "error": code,
        "message": message,
    }
    if hint:
        body["hint"] = hint
    if extra:
        body.update(extra)
    return body


def upload_error(message: str) -> Dict[str, Any]:
    return error_detail(
        "upload_failed",
        message,
        hint="Zip must include agent.yaml and agent.py at root or in one folder. Max 10 MB.",
    )


def quota_error(message: str) -> Dict[str, Any]:
    return error_detail(
        "usage_quota_exceeded",
        message,
        hint="Check GET /billing/limits or upgrade your plan.",
    )


def deployment_error(message: str) -> Dict[str, Any]:
    return error_detail(
        "deployment_failed",
        message,
        hint="Fix the artifact, re-upload, then deploy again.",
    )


def deployment_already_active(deployment: Dict[str, Any]) -> Dict[str, Any]:
    dep_id = deployment.get("deployment_id", "")
    return error_detail(
        "deployment_already_active",
        "This version is already active for this project.",
        hint="Run a task or open Runs & traces instead of redeploying.",
        extra={
            "deployment_id": dep_id,
            "deployment": deployment,
            "actions": {
                "run": f"/deployments/{dep_id}/run",
                "deployments": "/deployments",
                "runs": "/runs",
            },
        },
    )


def auth_error(message: str) -> Dict[str, Any]:
    return error_detail(
        "auth_failed",
        message,
        hint="Use Authorization: Bearer <token> or ak_live_* API key.",
    )
