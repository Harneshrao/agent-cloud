"""
Product Layer: Marketplace browsing API.

GET /marketplace/agents — Browse agents with product-shaped response.
Returns: agent_name, description, developer, rating, price_per_run, input_schema, example_output.
Filters: category (capabilities), popularity, price, rating.

No infrastructure concepts (workers, queues, DAG, regions) are exposed.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from database.agent_store import list_published_agents
from database.agent_pricing import get_price as get_agent_pricing
from database.agent_ratings import get_average_rating_for_agent
from database.agent_installations import get_agent_input_schema
from database.usage_records import get_recent_runs_by_agent
from database.agent_installs import count_projects_using_agent
from database.developer_economy import (
    list_approved_agents_for_marketplace,
    get_install_stats,
    get_developer_profile_by_id,
)
from database.agent_production_hardening import get_trust_metrics

# Ranking weights: rank_score = 0.4*installs + 0.3*rating + 0.2*success_rate + 0.1*revenue (each component normalized 0-1)
RANK_WEIGHT_INSTALLS = 0.4
RANK_WEIGHT_RATING = 0.3
RANK_WEIGHT_SUCCESS_RATE = 0.2
RANK_WEIGHT_REVENUE = 0.1


def _compute_rank_score(
    install_count: int,
    rating: float | None,
    success_rate: float,
    revenue_total: float,
) -> float:
    """Normalize components to 0-1 and compute weighted rank_score."""
    installs_norm = min(1.0, (install_count or 0) / 100.0)
    rating_norm = ((rating - 1) / 4.0) if rating is not None and rating >= 1 else 0.5
    revenue_norm = min(1.0, (revenue_total or 0) / 500.0)
    return round(
        RANK_WEIGHT_INSTALLS * installs_norm
        + RANK_WEIGHT_RATING * rating_norm
        + RANK_WEIGHT_SUCCESS_RATE * success_rate
        + RANK_WEIGHT_REVENUE * revenue_norm,
        4,
    )


router = APIRouter(prefix="/marketplace", tags=["marketplace"])


def _example_output_for_agent(agent_name: str):
    """Get example_output from registry (optional agent class attribute)."""
    try:
        from registry.agent_registry import agent_registry
        agent = agent_registry.get_agent(agent_name)
        if agent is not None:
            return getattr(agent, "example_output", None)
    except Exception:
        pass
    return None


def _build_marketplace_agents_list():
    """Build list of agents: prefer approved developer-economy agents (developer name, verified, install_count, price). Merge with legacy agents."""
    recent_runs = get_recent_runs_by_agent(30)
    seen_names = set()
    out = []

    # Approved developer-economy agents (marketplace shows only approved)
    try:
        approved = list_approved_agents_for_marketplace()
        for a in approved:
            name = a.get("agent_name") or ""
            if not name or name in seen_names:
                continue
            seen_names.add(name)
            dev_profile = get_developer_profile_by_id(a["developer_id"]) if a.get("developer_id") else None
            stats = get_install_stats(a["agent_id"]) if a.get("agent_id") else None
            install_count = stats["installs_total"] if stats else count_projects_using_agent(name)
            revenue_total = stats["revenue_total"] if stats else 0.0
            rating = get_average_rating_for_agent(name)
            trust = get_trust_metrics(name)
            success_rate = float(trust["success_rate"]) if trust and trust.get("runs_total", 0) > 0 else 0.5
            rank_score = _compute_rank_score(install_count, rating, success_rate, revenue_total)
            input_schema = get_agent_input_schema(name)
            example_output = _example_output_for_agent(name)
            popularity = recent_runs.get(name, 0) + install_count * 2
            created_at = a.get("created_at")
            if hasattr(created_at, "isoformat"):
                created_at = created_at.isoformat()
            out.append({
                "agent_id": a.get("agent_id"),
                "agent_name": name,
                "description": a.get("description") or "",
                "developer": (dev_profile.get("display_name") or dev_profile.get("company_name") or "") if dev_profile else "",
                "developer_verified": bool(dev_profile.get("verified")) if dev_profile else False,
                "version": None,
                "rating": rating,
                "price_per_run": float(a.get("price_per_run") or 0),
                "currency": a.get("currency") or "USD",
                "input_schema": input_schema,
                "example_output": example_output,
                "capabilities": [a.get("category")] if a.get("category") else [],
                "popularity": popularity,
                "install_count": install_count,
                "rank_score": rank_score,
                "success_rate": success_rate,
                "created_at": created_at,
            })
    except Exception:
        pass

    # Legacy agents (from agent_store) not already in approved list
    published = list_published_agents()
    for a in published:
        name = a.get("name") or ""
        if not name or name in seen_names:
            continue
        seen_names.add(name)
        pricing = get_agent_pricing(name)
        price_per_run = float(pricing["price_per_run"]) if pricing else 0.0
        currency = pricing.get("currency") or "USD"
        rating = get_average_rating_for_agent(name)
        input_schema = get_agent_input_schema(name)
        example_output = _example_output_for_agent(name)
        install_count = count_projects_using_agent(name)
        trust = get_trust_metrics(name)
        success_rate = float(trust["success_rate"]) if trust and trust.get("runs_total", 0) > 0 else 0.5
        rank_score = _compute_rank_score(install_count, rating, success_rate, 0.0)
        popularity = recent_runs.get(name, 0) + install_count * 2
        out.append({
            "agent_id": a.get("id"),
            "agent_name": name,
            "description": a.get("description") or "",
            "developer": a.get("author") or "",
            "developer_verified": False,
            "version": a.get("version"),
            "rating": rating,
            "price_per_run": price_per_run,
            "currency": currency,
            "input_schema": input_schema,
            "example_output": example_output,
            "capabilities": a.get("capabilities") or [],
            "popularity": popularity,
            "install_count": install_count,
            "rank_score": rank_score,
            "success_rate": success_rate,
            "created_at": a.get("created_at"),
        })
    return out


@router.get("/agents")
def list_marketplace_agents(
    category: str | None = Query(None, description="Filter by category/capability"),
    sort: str | None = Query(None, description="Sort: rank | popularity | price_asc | price_desc | rating"),
    min_rating: float | None = Query(None, description="Minimum average rating"),
    max_price: float | None = Query(None, description="Maximum price_per_run"),
):
    """
    Browse marketplace agents. Product-shaped response for non-technical users.
    No workers, queues, or infrastructure concepts.
    """
    try:
        agents = _build_marketplace_agents_list()
    except Exception:
        agents = []
    if category:
        cat = category.strip().lower()
        agents = [a for a in agents if cat in [c.lower() for c in (a.get("capabilities") or [])]]
    if min_rating is not None:
        agents = [a for a in agents if (a.get("rating") or 0) >= min_rating]
    if max_price is not None:
        agents = [a for a in agents if (a.get("price_per_run") or 0) <= max_price]
    if sort:
        if sort == "rank":
            agents = sorted(agents, key=lambda x: x.get("rank_score") or 0, reverse=True)
        elif sort == "popularity":
            agents = sorted(agents, key=lambda x: x.get("popularity") or 0, reverse=True)
        elif sort == "price_asc":
            agents = sorted(agents, key=lambda x: x.get("price_per_run") or 0)
        elif sort == "price_desc":
            agents = sorted(agents, key=lambda x: x.get("price_per_run") or 0, reverse=True)
        elif sort == "rating":
            agents = sorted(agents, key=lambda x: x.get("rating") or 0, reverse=True)
    else:
        # Default: sort by rank_score (0.4*installs + 0.3*rating + 0.2*success_rate + 0.1*revenue)
        agents = sorted(agents, key=lambda x: x.get("rank_score") or 0, reverse=True)
    return {"agents": agents}


def _apply_search_query(agents: list, query: str) -> list:
    """Filter agents where query (case-insensitive) appears in agent_name, description, or capabilities."""
    if not query or not query.strip():
        return agents
    q = query.strip().lower()
    out = []
    for a in agents:
        name = (a.get("agent_name") or "").lower()
        desc = (a.get("description") or "").lower()
        caps = [str(c).lower() for c in (a.get("capabilities") or [])]
        if q in name or q in desc or any(q in c for c in caps):
            out.append(a)
    return out


def _apply_sort(agents: list, sort: str | None) -> list:
    """Sort agents by popularity | rating | price | rank_score | newest."""
    if not sort:
        return sorted(agents, key=lambda x: x.get("rank_score") or 0, reverse=True)
    if sort == "popularity":
        return sorted(agents, key=lambda x: x.get("popularity") or 0, reverse=True)
    if sort == "rating":
        return sorted(agents, key=lambda x: x.get("rating") or 0, reverse=True)
    if sort == "price":
        return sorted(agents, key=lambda x: x.get("price_per_run") or 0)
    if sort == "price_desc":
        return sorted(agents, key=lambda x: x.get("price_per_run") or 0, reverse=True)
    if sort == "rank_score":
        return sorted(agents, key=lambda x: x.get("rank_score") or 0, reverse=True)
    if sort == "newest":
        return sorted(agents, key=lambda x: x.get("created_at") or "", reverse=True)
    return sorted(agents, key=lambda x: x.get("rank_score") or 0, reverse=True)


@router.get("/search")
def search_marketplace(
    query: str | None = Query(None, description="Search in agent_name, description, capabilities (LIKE %query%)"),
    category: str | None = Query(None, description="Filter by category/capability"),
    min_rating: float | None = Query(None, description="Minimum average rating"),
    max_price: float | None = Query(None, description="Maximum price_per_run"),
    sort: str | None = Query(None, description="Sort: popularity | rating | price | rank_score | newest"),
):
    """
    Search and filter marketplace agents. Search fields: agent_name, description, capabilities.
    """
    try:
        agents = _build_marketplace_agents_list()
    except Exception:
        agents = []
    if query:
        agents = _apply_search_query(agents, query)
    if category:
        cat = category.strip().lower()
        agents = [a for a in agents if cat in [c.lower() for c in (a.get("capabilities") or [])]]
    if min_rating is not None:
        agents = [a for a in agents if (a.get("rating") or 0) >= min_rating]
    if max_price is not None:
        agents = [a for a in agents if (a.get("price_per_run") or 0) <= max_price]
    agents = _apply_sort(agents, sort)
    return {"agents": agents}


@router.get("/recommendations")
def get_recommendations(
    limit: int = Query(10, ge=1, le=50, description="Max number of agents to return"),
):
    """
    Recommended agents: top by installs, highest ratings, and rank_score (growth/popularity).
    """
    try:
        agents = _build_marketplace_agents_list()
    except Exception:
        agents = []
    # Sort by rank_score (combines installs, rating, success_rate, revenue) then take top
    agents = sorted(agents, key=lambda x: x.get("rank_score") or 0, reverse=True)
    return {"agents": agents[:limit]}
