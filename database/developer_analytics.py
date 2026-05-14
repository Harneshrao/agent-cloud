"""
Developer dashboard analytics: agent runs, revenue, template installs, package installs.

Queries are scoped by developer user_id (agents/templates they own).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from database.db import db
from database.agent_pricing import get_price
from database.agent_ratings import get_average_rating_for_agent
from database.agent_usage_stats import get_stats_for_agent
from database.agent_revenue import get_revenue_summary


def get_agent_names_by_developer(developer_user_id: int) -> List[str]:
    """Return list of agent names where agent_pricing.developer_user_id = developer_user_id."""
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT agent_name FROM agent_pricing WHERE developer_user_id = ?",
        (developer_user_id,),
    )
    return [row["agent_name"] for row in cur.fetchall()]


def get_developer_agent_runs(developer_user_id: int) -> int:
    """Total runs across all agents owned by this developer."""
    from database.agent_usage_stats import get_all_stats
    agent_names = set(get_agent_names_by_developer(developer_user_id))
    if not agent_names:
        return 0
    total = 0
    for name in agent_names:
        stats = get_stats_for_agent(name)
        if stats:
            total += stats.get("runs", 0)
    return total


def get_developer_revenue(developer_user_id: int) -> float:
    """Total revenue (developer_share) for this developer."""
    summary = get_revenue_summary(developer_user_id)
    return summary.get("total_earned", 0.0)


def get_developer_template_installs(developer_user_id: int) -> int:
    """Count of template_installs for templates where author_user_id = developer_user_id."""
    try:
        from database import template_installs
        from database import workflow_templates
        template_installs._ensure_schema()
        workflow_templates._ensure_schema()
    except Exception:
        pass
    cur = db.get_connection().cursor()
    try:
        cur.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM template_installs ti
            JOIN workflow_templates t ON t.id = ti.template_id
            WHERE t.author_user_id = ?
            """,
            (developer_user_id,),
        )
        row = cur.fetchone()
        return int(row["cnt"]) if row and row["cnt"] is not None else 0
    except Exception:
        return 0


def get_total_package_installs() -> int:
    """Total package install count across all packages (from package_stats)."""
    try:
        from database.package_stats import get_all_package_stats
        stats = get_all_package_stats()
        return sum(s["install_count"] for s in stats)
    except Exception:
        return 0


def get_developer_ratings_summary(developer_user_id: int) -> Dict[str, Any]:
    """Average rating and count of ratings for agents owned by this developer."""
    agent_names = get_agent_names_by_developer(developer_user_id)
    if not agent_names:
        return {"average": None, "count": 0}
    ratings = []
    for name in agent_names:
        avg = get_average_rating_for_agent(name)
        if avg is not None:
            ratings.append(avg)
    cur = db.get_connection().cursor()
    placeholders = ",".join("?" * len(agent_names))
    cur.execute(
        f"SELECT COUNT(*) AS cnt FROM agent_ratings WHERE agent_name IN ({placeholders})",
        agent_names,
    )
    row = cur.fetchone()
    count = int(row["cnt"]) if row and row["cnt"] is not None else 0
    average = round(sum(ratings) / len(ratings), 2) if ratings else None
    return {"average": average, "count": count}


def get_developer_dashboard(developer_user_id: int) -> Dict[str, Any]:
    """
    Aggregate dashboard: agents (with runs, revenue, average_rating), revenue, runs, ratings,
    template_installs, package_installs.
    """
    agent_names = get_agent_names_by_developer(developer_user_id)
    agents = []
    total_runs = 0
    total_revenue = 0.0
    rating_values = []

    for name in agent_names:
        stats = get_stats_for_agent(name)
        runs = stats.get("runs", 0) if stats else 0
        total_runs += runs

        rev = _get_agent_revenue_for_developer(name, developer_user_id)
        total_revenue += rev

        avg_rating = get_average_rating_for_agent(name)
        if avg_rating is not None:
            rating_values.append(avg_rating)

        agents.append({
            "agent_name": name,
            "runs": runs,
            "revenue": round(rev, 2),
            "average_rating": avg_rating,
        })

    ratings_summary = get_developer_ratings_summary(developer_user_id)
    template_installs = get_developer_template_installs(developer_user_id)
    package_installs = get_total_package_installs()

    return {
        "agents": agents,
        "revenue": round(total_revenue, 2),
        "runs": total_runs,
        "ratings": ratings_summary,
        "template_installs": template_installs,
        "package_installs": package_installs,
    }


def _get_agent_revenue_for_developer(agent_name: str, developer_user_id: int) -> float:
    """Sum of developer_share from agent_revenue for this agent and developer."""
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT COALESCE(SUM(developer_share), 0) AS total
        FROM agent_revenue
        WHERE agent_name = ? AND developer_user_id = ?
        """,
        (agent_name, developer_user_id),
    )
    row = cur.fetchone()
    return float(row["total"]) if row and row["total"] is not None else 0.0


def get_agent_stats_for_developer(agent_name: str, developer_user_id: int) -> Optional[Dict[str, Any]]:
    """
    Per-agent stats (runs, revenue, average_rating) if this developer owns the agent.
    Returns None if not owned.
    """
    pricing = get_price(agent_name)
    if not pricing or pricing.get("developer_user_id") != developer_user_id:
        return None
    stats = get_stats_for_agent(agent_name)
    runs = stats.get("runs", 0) if stats else 0
    revenue = _get_agent_revenue_for_developer(agent_name, developer_user_id)
    average_rating = get_average_rating_for_agent(agent_name)
    return {
        "agent_name": agent_name,
        "runs": runs,
        "revenue": round(revenue, 2),
        "average_rating": average_rating,
    }
