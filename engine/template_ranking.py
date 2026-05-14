"""
Template ranking for marketplace: runs, average rating, recency.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Dict, List

from database.workflow_templates import (
    get_average_rating_for_template,
    list_templates,
)


def _recency_score(last_run_at: Any, half_life_days: float = 30.0) -> float:
    if last_run_at is None:
        return 0.0
    if hasattr(last_run_at, "year"):
        dt = last_run_at
    elif isinstance(last_run_at, str):
        try:
            dt = datetime.fromisoformat(last_run_at.replace("Z", "+00:00"))
        except Exception:
            return 0.0
    else:
        return 0.0
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    days = (now - dt).total_seconds() / 86400
    if days <= 0:
        return 1.0
    return math.exp(-0.693 * days / half_life_days)


def _score(
    run_count: int,
    avg_rating: float | None,
    last_run_at: Any,
    *,
    weight_runs: float = 0.4,
    weight_rating: float = 0.35,
    weight_recency: float = 0.25,
    recency_half_life_days: float = 30.0,
) -> float:
    run_score = min(1.0, math.log1p(run_count) / math.log1p(1000))
    rating_norm = (avg_rating / 5.0) if avg_rating is not None else 0.0
    recency = _recency_score(last_run_at, half_life_days=recency_half_life_days)
    return weight_runs * run_score + weight_rating * rating_norm + weight_recency * recency


def get_top_templates(limit: int = 20) -> List[Dict[str, Any]]:
    """Rank templates by runs, rating, recency (balanced)."""
    templates = list_templates(limit=500)
    scored = []
    for t in templates:
        avg = get_average_rating_for_template(t["id"])
        sc = _score(
            t["run_count"],
            avg,
            t.get("last_run_at"),
            weight_runs=0.4,
            weight_rating=0.35,
            weight_recency=0.25,
        )
        scored.append({**t, "average_rating": avg, "score": round(sc, 4)})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:limit]


def get_trending_templates(limit: int = 20) -> List[Dict[str, Any]]:
    """Rank templates with higher weight on recency."""
    templates = list_templates(limit=500)
    scored = []
    for t in templates:
        avg = get_average_rating_for_template(t["id"])
        sc = _score(
            t["run_count"],
            avg,
            t.get("last_run_at"),
            weight_runs=0.25,
            weight_rating=0.25,
            weight_recency=0.5,
            recency_half_life_days=14.0,
        )
        scored.append({**t, "average_rating": avg, "score": round(sc, 4)})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:limit]
