"""
Agent ranking for marketplace discovery.

Ranking score: score = runs * 3 + average_rating * 10 + recent_runs * 5
Used by GET /agents/top (recent_runs = last 30 days) and GET /agents/trending (recent_runs = last 7 days).
"""

from __future__ import annotations

from typing import Any, Dict, List

from database.agent_ratings import get_average_rating_for_agent
from database.agent_usage_stats import get_all_stats, refresh_from_usage_records
from database.usage_records import get_recent_runs_by_agent


def ranking_score(
    runs: int,
    average_rating: float | None,
    recent_runs: int,
) -> float:
    """
    Compute ranking score: runs*3 + average_rating*10 + recent_runs*5.
    Rating is 1-5; use 0 if no ratings.
    """
    avg = average_rating if average_rating is not None else 0.0
    return runs * 3 + avg * 10 + recent_runs * 5


def get_top_agents(limit: int = 20) -> List[Dict[str, Any]]:
    """
    Rank agents by score = runs*3 + average_rating*10 + recent_runs*5.
    recent_runs = runs in last 30 days.
    """
    refresh_from_usage_records()
    recent = get_recent_runs_by_agent(days=30)
    stats = get_all_stats()
    scored = []
    for s in stats:
        name = s["agent_name"]
        avg_rating = get_average_rating_for_agent(name)
        recent_runs = recent.get(name, 0)
        sc = ranking_score(s["runs"], avg_rating, recent_runs)
        scored.append({
            "agent_name": name,
            "runs": s["runs"],
            "avg_execution_time": s["avg_execution_time"],
            "last_used_at": s.get("last_used_at"),
            "last_run_at": s.get("last_used_at"),
            "average_rating": avg_rating,
            "recent_runs": recent_runs,
            "score": round(sc, 4),
        })
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:limit]


def get_trending_agents(limit: int = 20) -> List[Dict[str, Any]]:
    """
    Rank agents by score with recent_runs = runs in last 7 days (trending).
    """
    refresh_from_usage_records()
    recent = get_recent_runs_by_agent(days=7)
    stats = get_all_stats()
    scored = []
    for s in stats:
        name = s["agent_name"]
        avg_rating = get_average_rating_for_agent(name)
        recent_runs = recent.get(name, 0)
        sc = ranking_score(s["runs"], avg_rating, recent_runs)
        scored.append({
            "agent_name": name,
            "runs": s["runs"],
            "avg_execution_time": s["avg_execution_time"],
            "last_used_at": s.get("last_used_at"),
            "last_run_at": s.get("last_used_at"),
            "average_rating": avg_rating,
            "recent_runs": recent_runs,
            "score": round(sc, 4),
        })
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:limit]
