#!/usr/bin/env python3
"""
PMF scorecard rollup for First 5 users — reads product_events from DB.

Usage:
  py -3.11 scripts/user_research_report.py
  py -3.11 scripts/user_research_report.py --days 14
"""

from __future__ import annotations

import argparse
import os
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

STEP_LABELS = {
    "signup_completed": "Signup",
    "project_created": "Project",
    "deployment_created": "Deploy",
    "first_task_completed": "First run",
    "trace_viewed": "Trace",
    "api_key_created": "API key",
    "user_research_session_completed": "Session PMF",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="User research cohort scorecard")
    parser.add_argument("--days", type=int, default=30, help="Lookback window")
    args = parser.parse_args()

    from datetime import datetime, timedelta, timezone

    from database import product_events as pe
    from services.pmf_metrics import get_funnel_summary, get_trust_metrics

    since = datetime.now(timezone.utc) - timedelta(days=args.days)
    cohort = pe.list_user_cohort_progress(limit=5, since=since)
    funnel = get_funnel_summary(days=args.days)
    trust = get_trust_metrics(days=args.days)

    print("")
    print("Agent Cloud — user research scorecard")
    print("=" * 56)
    print(f"Window: {args.days} days")
    print("")

    signups = funnel.get("signup_users") or 0
    activated = funnel.get("activated_users") or 0
    deploy_denom = max(signups, len(cohort), 1)
    run_pct = round(100.0 * activated / deploy_denom, 1) if deploy_denom else 0

    completed_traces = sum(1 for u in cohort if u.get("steps", {}).get("trace_viewed"))
    keys = sum(1 for u in cohort if u.get("steps", {}).get("api_key_created"))
    research = [u for u in cohort if u.get("would_use_again") is not None]
    would_again = sum(1 for u in research if int(u.get("would_use_again") or 0) >= 4)
    needed_help = sum(1 for u in research if u.get("needed_help") is True)

    ttas = [
        u["time_to_activation_seconds"]
        for u in cohort
        if u.get("time_to_activation_seconds") is not None
    ]
    median_tta = "-"
    if ttas:
        ttas.sort()
        mid = len(ttas) // 2
        median_tta = f"{round(ttas[mid] / 60, 1)} min"

    print("Cohort metrics")
    print("-" * 56)
    print(f"  Users tracked:           {len(cohort)}")
    print(f"  First run success:       {run_pct}% ({activated}/{deploy_denom})")
    print(f"  Trace viewed:            {completed_traces}/{len(cohort) or '-'}")
    print(f"  API keys created:        {keys}/{len(cohort) or '-'}")
    print(f"  Median time to success:  {median_tta}")
    print(f"  Would use again (>=4):   {would_again}/{len(research) or '-'}")
    print(f"  Needed founder help:     {needed_help}/{len(research) or '-'}")
    print(f"  Task success rate:       {trust.get('task_success_rate_pct')}%")
    print("")

    if not cohort:
        print("No users in window — invite testers and re-run.")
        print("Docs: docs/FIRST_5_USERS.md")
        print("")
        return 0

    print("Per-user funnel")
    print("-" * 56)
    for i, u in enumerate(cohort, 1):
        steps = u.get("steps") or {}
        flags = " ".join(
            f"{STEP_LABELS.get(k, k)[0] if steps.get(k) else '·'}"
            for k in (
                "project_created",
                "deployment_created",
                "first_task_completed",
                "trace_viewed",
                "api_key_created",
            )
        )
        tta = u.get("time_to_activation_seconds")
        tta_s = f"{round(tta / 60, 1)}m" if tta else "-"
        again = u.get("would_use_again", "-")
        help_ = "yes" if u.get("needed_help") else "no" if u.get("needed_help") is False else "-"
        print(
            f"  {i}. {u['user_id'][:8]}..  TTA={tta_s}  [{flags}]  again={again}  help={help_}"
        )
    print("")
    print("Legend: P=project D=deploy R=run T=trace K=key")
    print("Scorecard template: docs/templates/USER_SESSION_SCORECARD.md")
    print("=" * 56)
    print("")
    return 0


if __name__ == "__main__":
    sys.exit(main())
