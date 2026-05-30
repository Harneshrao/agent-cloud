"""
Product analytics events — activation funnel and PMF measurement.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, func, select

from database.models import ProductEvent, UsageEvent
from database.session import SessionLocal

# Canonical event names (activation funnel order)
EVENT_SIGNUP = "signup_completed"
EVENT_LOGIN = "login_completed"
EVENT_PROJECT_CREATED = "project_created"
EVENT_PROJECT_SELECTED = "project_selected"
EVENT_ARTIFACT_UPLOAD_SUCCEEDED = "artifact_upload_succeeded"
EVENT_ARTIFACT_UPLOAD_FAILED = "artifact_upload_failed"
EVENT_DEPLOYMENT_CREATED = "deployment_created"
EVENT_DEPLOYMENT_FAILED = "deployment_failed"
EVENT_DEPLOYMENT_SAMPLE = "deployment_sample_requested"
EVENT_DEPLOYMENT_ROLLBACK = "deployment_rollback"
EVENT_FIRST_TASK_COMPLETED = "first_task_completed"
EVENT_FIRST_TASK_FAILED = "first_task_failed"
EVENT_LOGS_VIEWED = "logs_viewed"
EVENT_TRACE_VIEWED = "trace_viewed"
EVENT_RETRY_CLICKED = "retry_clicked"
EVENT_DLQ_VIEWED = "dlq_viewed"
EVENT_API_KEY_CREATED = "api_key_created"
EVENT_ONBOARDING_STEP = "onboarding_step"
EVENT_FEEDBACK = "feedback_submitted"
EVENT_USER_RESEARCH_SESSION = "user_research_session_completed"
EVENT_PAGE_VIEW = "page_viewed"
EVENT_RUN_CTA_CLICKED = "run_cta_clicked"
EVENT_RUN_AGAIN_CLICKED = "run_again_clicked"
EVENT_SECOND_TASK_STARTED = "second_task_started"
EVENT_DEPLOY_WITHOUT_RUN_VIEW = "deploy_without_run_view"

FUNNEL_STEPS = [
    EVENT_SIGNUP,
    EVENT_PROJECT_CREATED,
    EVENT_ARTIFACT_UPLOAD_SUCCEEDED,
    EVENT_DEPLOYMENT_CREATED,
    EVENT_FIRST_TASK_COMPLETED,
    EVENT_TRACE_VIEWED,
    EVENT_API_KEY_CREATED,
]


def insert_product_event(
    event_name: str,
    *,
    user_id: Optional[uuid.UUID] = None,
    project_id: Optional[uuid.UUID] = None,
    deployment_id: Optional[uuid.UUID] = None,
    task_id: Optional[uuid.UUID] = None,
    session_id: Optional[str] = None,
    onboarding_step: Optional[str] = None,
    source: str = "client",
    properties: Optional[dict] = None,
) -> uuid.UUID:
    with SessionLocal() as session:
        row = ProductEvent(
            event_name=event_name,
            user_id=user_id,
            project_id=project_id,
            deployment_id=deployment_id,
            task_id=task_id,
            session_id=session_id,
            onboarding_step=onboarding_step,
            source=source,
            properties=properties or {},
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return row.id


def has_project_event(project_id: uuid.UUID, event_name: str) -> bool:
    with SessionLocal() as session:
        n = session.scalar(
            select(func.count())
            .select_from(ProductEvent)
            .where(
                ProductEvent.project_id == project_id,
                ProductEvent.event_name == event_name,
            )
        )
        return int(n or 0) > 0


def count_distinct_users(event_name: str, *, since: datetime) -> int:
    with SessionLocal() as session:
        n = session.scalar(
            select(func.count(func.distinct(ProductEvent.user_id))).where(
                ProductEvent.event_name == event_name,
                ProductEvent.created_at >= since,
                ProductEvent.user_id.isnot(None),
            )
        )
        return int(n or 0)


def count_distinct_sessions(event_name: str, *, since: datetime) -> int:
    with SessionLocal() as session:
        n = session.scalar(
            select(func.count(func.distinct(ProductEvent.session_id))).where(
                ProductEvent.event_name == event_name,
                ProductEvent.created_at >= since,
                ProductEvent.session_id.isnot(None),
            )
        )
        return int(n or 0)


def count_events_since(event_name: str, *, since: datetime) -> int:
    with SessionLocal() as session:
        n = session.scalar(
            select(func.count())
            .select_from(ProductEvent)
            .where(
                ProductEvent.event_name == event_name,
                ProductEvent.created_at >= since,
            )
        )
        return int(n or 0)


def median_time_to_event(
    from_event: str,
    to_event: str,
    *,
    since: datetime,
) -> Optional[float]:
    """Median seconds from first from_event to first to_event per user (with both)."""
    with SessionLocal() as session:
        from_rows = session.execute(
            select(ProductEvent.user_id, func.min(ProductEvent.created_at).label("t0"))
            .where(
                ProductEvent.event_name == from_event,
                ProductEvent.created_at >= since,
                ProductEvent.user_id.isnot(None),
            )
            .group_by(ProductEvent.user_id)
        ).all()
        if not from_rows:
            return None
        deltas: List[float] = []
        for user_id, t0 in from_rows:
            t1 = session.scalar(
                select(func.min(ProductEvent.created_at)).where(
                    ProductEvent.user_id == user_id,
                    ProductEvent.event_name == to_event,
                    ProductEvent.created_at >= t0,
                )
            )
            if t1 is not None:
                deltas.append((t1 - t0).total_seconds())
        if not deltas:
            return None
        deltas.sort()
        mid = len(deltas) // 2
        if len(deltas) % 2:
            return deltas[mid]
        return (deltas[mid - 1] + deltas[mid]) / 2.0


def usage_counts_by_type(
    *,
    since: datetime,
    event_types: List[str],
) -> Dict[str, int]:
    with SessionLocal() as session:
        rows = session.execute(
            select(UsageEvent.event_type, func.count())
            .where(
                UsageEvent.created_at >= since,
                UsageEvent.event_type.in_(event_types),
            )
            .group_by(UsageEvent.event_type)
        ).all()
        return {str(et): int(c) for et, c in rows}


def count_distinct_users_with_event_without(
    has_event: str,
    without_event: str,
    *,
    since: datetime,
) -> int:
    """Users with has_event in window who never recorded without_event (any time)."""
    with SessionLocal() as session:
        has_users = session.scalars(
            select(ProductEvent.user_id)
            .where(
                ProductEvent.event_name == has_event,
                ProductEvent.created_at >= since,
                ProductEvent.user_id.isnot(None),
            )
            .distinct()
        ).all()
        if not has_users:
            return 0
        stuck = 0
        for user_id in has_users:
            n = session.scalar(
                select(func.count())
                .select_from(ProductEvent)
                .where(
                    ProductEvent.user_id == user_id,
                    ProductEvent.event_name == without_event,
                )
            )
            if int(n or 0) == 0:
                stuck += 1
        return stuck


def count_distinct_users_with_events(
    event_names: List[str],
    *,
    since: datetime,
) -> int:
    """Users who recorded every event in event_names within the window."""
    if not event_names:
        return 0
    with SessionLocal() as session:
        user_ids = session.scalars(
            select(ProductEvent.user_id)
            .where(
                ProductEvent.created_at >= since,
                ProductEvent.user_id.isnot(None),
            )
            .distinct()
        ).all()
        count = 0
        for user_id in user_ids:
            ok = True
            for ev in event_names:
                n = session.scalar(
                    select(func.count())
                    .select_from(ProductEvent)
                    .where(
                        ProductEvent.user_id == user_id,
                        ProductEvent.event_name == ev,
                        ProductEvent.created_at >= since,
                    )
                )
                if int(n or 0) == 0:
                    ok = False
                    break
            if ok:
                count += 1
        return count


def list_recent_feedback(*, limit: int = 20) -> List[Dict[str, Any]]:
    with SessionLocal() as session:
        rows = session.scalars(
            select(ProductEvent)
            .where(ProductEvent.event_name == EVENT_FEEDBACK)
            .order_by(desc(ProductEvent.created_at))
            .limit(limit)
        ).all()
        return [
            {
                "event_id": str(r.id),
                "user_id": str(r.user_id) if r.user_id else None,
                "project_id": str(r.project_id) if r.project_id else None,
                "created_at": r.created_at.isoformat(),
                "properties": r.properties,
            }
            for r in rows
        ]


def list_user_cohort_progress(*, limit: int = 5, since: datetime) -> List[Dict[str, Any]]:
    """
    Recent users with funnel step completion flags — for First 5 cohort tracking.
    """
    step_events = FUNNEL_STEPS + [EVENT_USER_RESEARCH_SESSION, EVENT_FEEDBACK]
    with SessionLocal() as session:
        user_rows = session.execute(
            select(
                ProductEvent.user_id,
                func.min(ProductEvent.created_at).label("first_seen"),
                func.max(ProductEvent.created_at).label("last_seen"),
            )
            .where(
                ProductEvent.created_at >= since,
                ProductEvent.user_id.isnot(None),
            )
            .group_by(ProductEvent.user_id)
            .order_by(desc(func.max(ProductEvent.created_at)))
            .limit(limit)
        ).all()
        out: List[Dict[str, Any]] = []
        for user_id, first_seen, _last_seen in user_rows:
            if user_id is None:
                continue
            flags: Dict[str, bool] = {}
            for ev in step_events:
                n = session.scalar(
                    select(func.count())
                    .select_from(ProductEvent)
                    .where(
                        ProductEvent.user_id == user_id,
                        ProductEvent.event_name == ev,
                        ProductEvent.created_at >= since,
                    )
                )
                flags[ev] = int(n or 0) > 0
            tta = session.scalar(
                select(func.min(ProductEvent.created_at)).where(
                    ProductEvent.user_id == user_id,
                    ProductEvent.event_name == EVENT_FIRST_TASK_COMPLETED,
                    ProductEvent.created_at >= since,
                )
            )
            tta_seconds = None
            if first_seen and tta:
                tta_seconds = round((tta - first_seen).total_seconds(), 1)
            research = session.scalars(
                select(ProductEvent)
                .where(
                    ProductEvent.user_id == user_id,
                    ProductEvent.event_name == EVENT_USER_RESEARCH_SESSION,
                    ProductEvent.created_at >= since,
                )
                .order_by(desc(ProductEvent.created_at))
                .limit(1)
            ).first()
            props = (research.properties or {}) if research else {}
            out.append(
                {
                    "user_id": str(user_id),
                    "first_seen": first_seen.isoformat() if first_seen else None,
                    "time_to_activation_seconds": tta_seconds,
                    "steps": flags,
                    "would_use_again": props.get("would_use_again"),
                    "needed_help": props.get("needed_help"),
                    "clarity_rating": props.get("clarity_rating"),
                }
            )
        return out
