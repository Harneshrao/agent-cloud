"""
Record product analytics events — never raise into user-facing flows.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from database import product_events as pe

_log = logging.getLogger(__name__)


def track(
    event_name: str,
    *,
    user_id: Optional[uuid.UUID] = None,
    project_id: Optional[uuid.UUID] = None,
    deployment_id: Optional[uuid.UUID] = None,
    task_id: Optional[uuid.UUID] = None,
    session_id: Optional[str] = None,
    onboarding_step: Optional[str] = None,
    source: str = "server",
    properties: Optional[dict[str, Any]] = None,
) -> None:
    try:
        pe.insert_product_event(
            event_name,
            user_id=user_id,
            project_id=project_id,
            deployment_id=deployment_id,
            task_id=task_id,
            session_id=session_id,
            onboarding_step=onboarding_step,
            source=source,
            properties=properties,
        )
    except Exception as exc:
        _log.debug("product_analytics track failed: %s", exc)


def track_once_per_project(
    event_name: str,
    project_id: uuid.UUID,
    **kwargs: Any,
) -> None:
    try:
        if pe.has_project_event(project_id, event_name):
            return
        track(event_name, project_id=project_id, **kwargs)
    except Exception as exc:
        _log.debug("product_analytics track_once failed: %s", exc)


def track_signup(user_id: uuid.UUID, *, email: str = "") -> None:
    track(pe.EVENT_SIGNUP, user_id=user_id, properties={"email": email[:120]})


def track_login(user_id: uuid.UUID) -> None:
    track(pe.EVENT_LOGIN, user_id=user_id)


def track_project_created(user_id: uuid.UUID, project_id: uuid.UUID, *, name: str = "") -> None:
    track(
        pe.EVENT_PROJECT_CREATED,
        user_id=user_id,
        project_id=project_id,
        properties={"name": name[:200]},
    )


def track_deployment_created(
    project_id: uuid.UUID,
    deployment_id: uuid.UUID,
    *,
    user_id: Optional[uuid.UUID] = None,
    sample: Optional[str] = None,
) -> None:
    props: dict[str, Any] = {}
    if sample:
        props["sample"] = sample
    track(
        pe.EVENT_DEPLOYMENT_CREATED,
        user_id=user_id,
        project_id=project_id,
        deployment_id=deployment_id,
        properties=props,
    )


def track_artifact_upload_failed(
    project_id: uuid.UUID,
    *,
    user_id: Optional[uuid.UUID] = None,
    error: str = "",
) -> None:
    track(
        pe.EVENT_ARTIFACT_UPLOAD_FAILED,
        user_id=user_id,
        project_id=project_id,
        properties={"error": error[:500]},
    )


def track_first_task_completed(
    project_id: uuid.UUID,
    task_id: uuid.UUID,
    *,
    deployment_id: Optional[uuid.UUID] = None,
) -> None:
    track_once_per_project(
        pe.EVENT_FIRST_TASK_COMPLETED,
        project_id,
        task_id=task_id,
        deployment_id=deployment_id,
        source="server",
    )
