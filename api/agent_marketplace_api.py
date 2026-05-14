"""
Agent marketplace ecosystem: ratings, rankings, developer analytics.

Endpoints:
  POST /agents/{name}/rate       - Submit a rating (project-scoped).
  GET  /agents/{name}/ratings   - List ratings for an agent.
  GET  /agents/top              - Top agents by runs, rating, recency.
  GET  /agents/trending         - Trending agents (recent usage weighted).
  GET  /developers/agents       - Developer analytics per agent.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from api.auth_api import get_current_user
from api.deps import require_project_context
from database.agent_installs import count_projects_using_agent
from database.agent_revenue import get_revenue_summary
from database.agent_ratings import add_rating, get_average_rating_for_agent, get_ratings_for_agent
from database.developer_analytics import get_developer_dashboard, get_agent_stats_for_developer
from database.agent_store import get_agent_by_name
from database.agent_usage_stats import get_all_stats, get_stats_for_agent, refresh_from_usage_records
from engine.agent_ranking import get_top_agents, get_trending_agents


# Mount under /agents; define /top and /trending before /{name}/... so they match first
router = APIRouter(prefix="/agents", tags=["marketplace-ecosystem"])
developers_router = APIRouter(prefix="/developers", tags=["developers"])


class RateAgentRequest(BaseModel):
    """Request body for POST /agents/{name}/rate."""

    rating: int = Field(..., ge=1, le=5, description="Rating 1-5")
    review: str | None = Field(None, description="Optional review text")


# ---------- /agents routes (order: /top, /trending before /{name}) ----------


@router.get("/top")
def agents_top(limit: int = Query(20, ge=1, le=100)):
    """Return top agents ranked by runs, average rating, and recent usage."""
    try:
        agents = get_top_agents(limit=limit)
        return {"agents": agents}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trending")
def agents_trending(limit: int = Query(20, ge=1, le=100)):
    """Return trending agents (higher weight on recent usage)."""
    try:
        agents = get_trending_agents(limit=limit)
        return {"agents": agents}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{name}/rate")
def agents_rate(
    name: str,
    data: RateAgentRequest,
    context: dict = Depends(require_project_context),
):
    """Submit a rating for an agent from the current project. Requires project context."""
    if get_agent_by_name(name) is None:
        raise HTTPException(status_code=404, detail=f"Agent '{name}' not found")
    try:
        rating = add_rating(
            agent_name=name,
            project_id=context["project_id"],
            rating=data.rating,
            review=data.review,
            user_id=context.get("user", {}).get("id"),
        )
        return {"status": "created", "rating": rating}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{name}/ratings")
def agents_ratings(name: str, limit: int = Query(100, ge=1, le=500)):
    """List ratings and reviews for an agent."""
    if get_agent_by_name(name) is None:
        raise HTTPException(status_code=404, detail=f"Agent '{name}' not found")
    try:
        ratings = get_ratings_for_agent(name, limit=limit)
        avg = get_average_rating_for_agent(name)
        return {"agent_name": name, "ratings": ratings, "average_rating": avg}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- /developers dashboard and agent stats ----------


@developers_router.get("/dashboard")
def developers_dashboard(user: dict = Depends(get_current_user)):
    """
    Developer dashboard: agents (with runs, revenue, average_rating), revenue, runs, ratings,
    template_installs, package_installs.
    """
    try:
        data = get_developer_dashboard(user["id"])
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@developers_router.get("/revenue")
def developers_revenue(user: dict = Depends(get_current_user)):
    """
    Revenue summary for the current developer: balance, total_earned, total_platform, recent revenue rows.
    """
    try:
        summary = get_revenue_summary(user["id"])
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@developers_router.get("/agents/{agent_name}/stats")
def developers_agent_stats(
    agent_name: str,
    user: dict = Depends(get_current_user),
):
    """Per-agent stats (runs, revenue, average_rating) for an agent owned by the current developer."""
    stats = get_agent_stats_for_developer(agent_name, user["id"])
    if stats is None:
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{agent_name}' not found or not owned by you",
        )
    return stats


@developers_router.get("/agents")
def developers_agents():
    """
    Developer analytics: runs_per_agent, average_rating, projects_using_agent
    for all agents with usage stats (and published agents with zeros where missing).
    """
    try:
        refresh_from_usage_records()
        stats = get_all_stats()
        out = []
        for s in stats:
            avg_rating = get_average_rating_for_agent(s["agent_name"])
            projects_count = count_projects_using_agent(s["agent_name"])
            out.append({
                "agent_name": s["agent_name"],
                "runs_per_agent": s["runs"],
                "average_rating": avg_rating,
                "projects_using_agent": projects_count,
                "avg_execution_time_ms": s["avg_execution_time"],
                "last_used_at": s.get("last_used_at"),
            })
        return {"agents": out}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
