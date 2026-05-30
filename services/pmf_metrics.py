"""
Founder-facing PMF aggregates — activation funnel, deployment health, trust signals.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from database import product_events as pe
from database.usage_events import (
    EVENT_TASK_COMPLETED,
    EVENT_TASK_DLQ,
    EVENT_TASK_FAILED,
    EVENT_TASK_RETRY,
    EVENT_DEPLOYMENT_CREATED,
    EVENT_ARTIFACT_UPLOADED,
)


def _since_days(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


def get_funnel_summary(*, days: int = 30) -> Dict[str, Any]:
    since = _since_days(days)
    steps: List[Dict[str, Any]] = []
    prev_users = 0
    for event_name in pe.FUNNEL_STEPS:
        users = pe.count_distinct_users(event_name, since=since)
        sessions = pe.count_distinct_sessions(event_name, since=since)
        count = max(users, sessions)
        drop_pct = 0.0
        if prev_users > 0 and count < prev_users:
            drop_pct = round(100.0 * (1 - count / prev_users), 1)
        steps.append(
            {
                "event": event_name,
                "unique_users": users,
                "unique_sessions": sessions,
                "count": count,
                "drop_off_pct_from_previous": drop_pct if prev_users else None,
            }
        )
        if count > 0:
            prev_users = count

    signup_users = pe.count_distinct_users(pe.EVENT_SIGNUP, since=since) or 1
    activated = pe.count_distinct_users(pe.EVENT_FIRST_TASK_COMPLETED, since=since)
    activation_rate = round(100.0 * activated / signup_users, 1) if signup_users else 0.0

    tta = pe.median_time_to_event(
        pe.EVENT_SIGNUP,
        pe.EVENT_FIRST_TASK_COMPLETED,
        since=since,
    )

    return {
        "window_days": days,
        "steps": steps,
        "activation_rate_pct": activation_rate,
        "median_time_to_activation_seconds": tta,
        "activated_users": activated,
        "signup_users": pe.count_distinct_users(pe.EVENT_SIGNUP, since=since),
    }


def get_deployment_health(*, days: int = 30) -> Dict[str, Any]:
    since = _since_days(days)
    usage = pe.usage_counts_by_type(
        since=since,
        event_types=[EVENT_ARTIFACT_UPLOADED, EVENT_DEPLOYMENT_CREATED],
    )
    uploads = usage.get(EVENT_ARTIFACT_UPLOADED, 0)
    deploys = usage.get(EVENT_DEPLOYMENT_CREATED, 0)
    upload_failures = pe.count_events_since(pe.EVENT_ARTIFACT_UPLOAD_FAILED, since=since)
    deploy_failures = pe.count_events_since(pe.EVENT_DEPLOYMENT_FAILED, since=since)
    rollbacks = pe.count_events_since(pe.EVENT_DEPLOYMENT_ROLLBACK, since=since)
    samples = pe.count_events_since(pe.EVENT_DEPLOYMENT_SAMPLE, since=since)

    success_denominator = uploads + upload_failures
    upload_success_pct = (
        round(100.0 * uploads / success_denominator, 1) if success_denominator else None
    )

    return {
        "window_days": days,
        "artifact_uploads": uploads,
        "artifact_upload_failures": upload_failures,
        "upload_success_rate_pct": upload_success_pct,
        "deployments_created": deploys,
        "deployment_failures": deploy_failures,
        "rollbacks": rollbacks,
        "sample_deploy_requests": samples,
    }


def get_activation_gaps(*, days: int = 30) -> Dict[str, Any]:
    """Drop-offs between deploy → run → trace → key → repeat."""
    since = _since_days(days)
    deployed = pe.count_distinct_users(pe.EVENT_DEPLOYMENT_CREATED, since=since)
    activated = pe.count_distinct_users(pe.EVENT_FIRST_TASK_COMPLETED, since=since)
    traced = pe.count_distinct_users(pe.EVENT_TRACE_VIEWED, since=since)
    keyed = pe.count_distinct_users(pe.EVENT_API_KEY_CREATED, since=since)

    deploy_without_run = pe.count_distinct_users_with_event_without(
        pe.EVENT_DEPLOYMENT_CREATED,
        pe.EVENT_FIRST_TASK_COMPLETED,
        since=since,
    )
    run_without_trace = pe.count_distinct_users_with_event_without(
        pe.EVENT_FIRST_TASK_COMPLETED,
        pe.EVENT_TRACE_VIEWED,
        since=since,
    )
    trace_without_key = pe.count_distinct_users_with_event_without(
        pe.EVENT_TRACE_VIEWED,
        pe.EVENT_API_KEY_CREATED,
        since=since,
    )

    second_task_starts = pe.count_events_since(pe.EVENT_SECOND_TASK_STARTED, since=since)
    run_again_clicks = pe.count_events_since(pe.EVENT_RUN_AGAIN_CLICKED, since=since)
    deploy_without_run_views = pe.count_events_since(pe.EVENT_DEPLOY_WITHOUT_RUN_VIEW, since=since)
    run_cta_clicks = pe.count_events_since(pe.EVENT_RUN_CTA_CLICKED, since=since)
    page_views = pe.count_events_since(pe.EVENT_PAGE_VIEW, since=since)

    repeat_users = pe.count_distinct_users(pe.EVENT_SECOND_TASK_STARTED, since=since)
    repeat_rate_pct = round(100.0 * repeat_users / activated, 1) if activated else None

    return {
        "window_days": days,
        "users_deployed": deployed,
        "users_first_run": activated,
        "users_trace_viewed": traced,
        "users_api_key": keyed,
        "deploy_without_run_users": deploy_without_run,
        "run_without_trace_users": run_without_trace,
        "trace_without_key_users": trace_without_key,
        "deploy_without_run_views": deploy_without_run_views,
        "run_cta_clicks": run_cta_clicks,
        "second_task_starts": second_task_starts,
        "run_again_clicks": run_again_clicks,
        "repeat_intent_users": repeat_users,
        "repeat_rate_pct": repeat_rate_pct,
        "page_views": page_views,
    }


def get_trust_metrics(*, days: int = 30) -> Dict[str, Any]:
    since = _since_days(days)
    usage = pe.usage_counts_by_type(
        since=since,
        event_types=[
            EVENT_TASK_COMPLETED,
            EVENT_TASK_FAILED,
            EVENT_TASK_RETRY,
            EVENT_TASK_DLQ,
        ],
    )
    completed = usage.get(EVENT_TASK_COMPLETED, 0)
    failed = usage.get(EVENT_TASK_FAILED, 0)
    retries = usage.get(EVENT_TASK_RETRY, 0)
    dlq = usage.get(EVENT_TASK_DLQ, 0)
    finished = completed + failed
    task_success_pct = round(100.0 * completed / finished, 1) if finished else None

    return {
        "window_days": days,
        "tasks_completed": completed,
        "tasks_failed": failed,
        "task_success_rate_pct": task_success_pct,
        "retries": retries,
        "dlq_entries": dlq,
        "logs_views": pe.count_events_since(pe.EVENT_LOGS_VIEWED, since=since),
        "trace_views": pe.count_events_since(pe.EVENT_TRACE_VIEWED, since=since),
        "retry_clicks": pe.count_events_since(pe.EVENT_RETRY_CLICKED, since=since),
        "onboarding_steps_completed": pe.count_events_since(pe.EVENT_ONBOARDING_STEP, since=since),
    }


def compute_pmf_health_score(
    *,
    activation_rate_pct: float,
    upload_success_rate_pct: float | None,
    task_success_rate_pct: float | None,
    onboarding_completion_proxy: float,
) -> Dict[str, Any]:
    """0–100 composite — measure reality, not vanity traffic."""
    upload = upload_success_rate_pct if upload_success_rate_pct is not None else 50.0
    tasks = task_success_rate_pct if task_success_rate_pct is not None else 50.0
    score = round(
        0.40 * min(activation_rate_pct, 100)
        + 0.25 * min(upload, 100)
        + 0.25 * min(tasks, 100)
        + 0.10 * min(onboarding_completion_proxy, 100),
        1,
    )
    label = "weak"
    if score >= 70:
        label = "strong"
    elif score >= 45:
        label = "emerging"
    return {"score": score, "label": label}


def get_alpha_ops_alerts(*, days: int = 7) -> List[Dict[str, Any]]:
    """Founder triage: spikes and abandonment signals for private alpha."""
    since = _since_days(days)
    alerts: List[Dict[str, Any]] = []

    deploy_fail = pe.count_events_since(pe.EVENT_DEPLOYMENT_FAILED, since=since)
    upload_fail = pe.count_events_since(pe.EVENT_ARTIFACT_UPLOAD_FAILED, since=since)
    if deploy_fail >= 3:
        alerts.append(
            {
                "severity": "high",
                "code": "deploy_failures",
                "message": f"{deploy_fail} deployment failures in {days}d — check traces & ZIP validation.",
            }
        )
    if upload_fail >= 3:
        alerts.append(
            {
                "severity": "medium",
                "code": "upload_failures",
                "message": f"{upload_fail} artifact upload failures in {days}d — review agent.yaml + agent.py.",
            }
        )

    usage = pe.usage_counts_by_type(
        since=since,
        event_types=[EVENT_TASK_DLQ, EVENT_TASK_RETRY, EVENT_TASK_FAILED],
    )
    dlq = usage.get(EVENT_TASK_DLQ, 0)
    retries = usage.get(EVENT_TASK_RETRY, 0)
    failed = usage.get(EVENT_TASK_FAILED, 0)
    if dlq >= 5:
        alerts.append(
            {
                "severity": "high",
                "code": "dlq_spike",
                "message": f"{dlq} tasks in DLQ ({days}d) — open DLQ page with users.",
            }
        )
    if retries >= 10:
        alerts.append(
            {
                "severity": "medium",
                "code": "retry_storm",
                "message": f"{retries} task retries ({days}d) — possible flaky agents or infra.",
            }
        )

    signups = pe.count_distinct_users(pe.EVENT_SIGNUP, since=since)
    activated = pe.count_distinct_users(pe.EVENT_FIRST_TASK_COMPLETED, since=since)
    if signups >= 2 and activated == 0:
        alerts.append(
            {
                "severity": "critical",
                "code": "activation_stall",
                "message": f"{signups} signups, 0 activations in {days}d — onboarding is broken.",
            }
        )
    elif signups > activated and signups - activated >= 2:
        alerts.append(
            {
                "severity": "medium",
                "code": "activation_gap",
                "message": f"{signups - activated} users stuck before first successful run.",
            }
        )

    low_feedback = [
        f
        for f in pe.list_recent_feedback(limit=20)
        if int((f.get("properties") or {}).get("rating") or 5) <= 2
    ]
    if low_feedback:
        alerts.append(
            {
                "severity": "medium",
                "code": "negative_feedback",
                "message": f"{len(low_feedback)} low ratings (≤2) — schedule user interview.",
            }
        )

    cohort = pe.list_user_cohort_progress(limit=5, since=since)
    help_count = sum(1 for u in cohort if u.get("needed_help") is True)
    low_again = sum(
        1
        for u in cohort
        if u.get("would_use_again") is not None and int(u.get("would_use_again") or 0) <= 2
    )
    if help_count >= 2:
        alerts.append(
            {
                "severity": "high",
                "code": "founder_help_pattern",
                "message": f"{help_count} recent users needed founder help — onboarding friction.",
            }
        )
    if low_again >= 2:
        alerts.append(
            {
                "severity": "medium",
                "code": "low_repeat_intent",
                "message": f"{low_again} users rated 'would use again' ≤2 — trust interview.",
            }
        )

    gaps = get_activation_gaps(days=min(days, 14))
    if gaps.get("deploy_without_run_users", 0) >= 1:
        alerts.append(
            {
                "severity": "high",
                "code": "deploy_without_run",
                "message": (
                    f"{gaps['deploy_without_run_users']} user(s) deployed but never completed a run — "
                    "check post-deploy Run CTA."
                ),
            }
        )
    if gaps.get("run_without_trace_users", 0) >= 1:
        alerts.append(
            {
                "severity": "medium",
                "code": "run_without_trace",
                "message": (
                    f"{gaps['run_without_trace_users']} user(s) ran but never opened a trace — "
                    "Runs & traces clarity issue."
                ),
            }
        )
    if gaps.get("trace_without_key_users", 0) >= 2:
        alerts.append(
            {
                "severity": "medium",
                "code": "trace_without_key",
                "message": (
                    f"{gaps['trace_without_key_users']} user(s) viewed trace but no API key — "
                    "post-success key CTA."
                ),
            }
        )
    if activated >= 2 and gaps.get("repeat_intent_users", 0) == 0:
        alerts.append(
            {
                "severity": "medium",
                "code": "no_second_run",
                "message": "Activated users but zero second-run signals — repeat loop may be unclear.",
            }
        )

    task_usage = pe.usage_counts_by_type(
        since=since,
        event_types=[EVENT_TASK_COMPLETED, EVENT_TASK_FAILED],
    )
    completed = task_usage.get(EVENT_TASK_COMPLETED, 0)
    if failed > 0 and failed > completed:
        alerts.append(
            {
                "severity": "high",
                "code": "task_reliability",
                "message": "More failures than completions — trust risk for alpha.",
            }
        )

    return alerts


def get_pmf_summary(*, days: int = 30) -> Dict[str, Any]:
    funnel = get_funnel_summary(days=days)
    deployment = get_deployment_health(days=days)
    trust = get_trust_metrics(days=days)

    since = _since_days(days)
    onboarding_events = pe.count_events_since(pe.EVENT_ONBOARDING_STEP, since=since)
    signup_users = funnel.get("signup_users") or 1
    onboarding_proxy = min(
        100.0,
        round(100.0 * onboarding_events / (signup_users * 5), 1),
    )

    health = compute_pmf_health_score(
        activation_rate_pct=float(funnel.get("activation_rate_pct") or 0),
        upload_success_rate_pct=deployment.get("upload_success_rate_pct"),
        task_success_rate_pct=trust.get("task_success_rate_pct"),
        onboarding_completion_proxy=onboarding_proxy,
    )

    return {
        "funnel": funnel,
        "deployment": deployment,
        "trust": trust,
        "activation_gaps": get_activation_gaps(days=days),
        "pmf_health": health,
        "ops_alerts": get_alpha_ops_alerts(days=min(days, 14)),
        "recent_feedback": pe.list_recent_feedback(limit=10),
        "user_research_cohort": pe.list_user_cohort_progress(limit=5, since=since),
        "targets": {
            "activation_rate_pct": 40,
            "upload_success_rate_pct": 80,
            "task_success_rate_pct": 85,
            "median_time_to_activation_minutes": 15,
        },
        "signals": {
            "pmf_positive": [
                "first_task_completed",
                "api_key_created",
                "trace_viewed after deploy",
                "retry_clicked (engaged debugging)",
            ],
            "churn_risk": [
                "artifact_upload_failed without recovery",
                "deployment_failed",
                "high dlq rate",
                "signup without project_created",
            ],
            "confusion": [
                "long time signup → first_task",
                "deploy without run",
                "feedback rating ≤ 2",
            ],
        },
    }
