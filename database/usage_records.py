"""
Usage records for metering: track per-task, per-agent execution for billing and dashboards.

Table: usage_records
  id, project_id, task_id, agent_name, execution_time_ms, tokens_used, created_at
"""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from database.db import db


def _ensure_schema() -> None:
    """Table is created by Alembic (UUID task_id / project_id)."""
    return


def _pid(project_id: Optional[uuid.UUID]) -> Optional[uuid.UUID]:
    return project_id


def record_usage(
    project_id: Optional[uuid.UUID],
    task_id: uuid.UUID,
    agent_name: str,
    execution_time_ms: int,
    tokens_used: int = 0,
    agent_cost: float = 0.0,
) -> int:
    """
    Insert a usage record after an agent run completes.
    agent_cost is the price_per_run for billing (monetization).
    Returns the new row id.
    """
    _ensure_schema()
    pid = _pid(project_id)
    cur = db.get_connection().cursor()
    cur.execute(
        """
        INSERT INTO usage_records
        (project_id, task_id, agent_name, execution_time_ms, tokens_used, agent_cost, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            pid,
            task_id,
            agent_name,
            execution_time_ms,
            tokens_used,
            agent_cost,
            datetime.utcnow(),
        ),
    )
    db.get_connection().commit()
    return int(cur.lastrowid)


def get_aggregated(
    project_id: uuid.UUID,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Return aggregated usage for a project within an optional date range.
    start_date / end_date are ISO date strings (YYYY-MM-DD); created_at is compared as date.

    Returns:
      total_runs: int
      total_execution_time_ms: int
      runs_per_agent: list of { agent_name, runs, total_execution_time_ms }
      usage_per_day: list of { date, runs, total_execution_time_ms } for dashboard charts
      top_agents: list of { agent_name, runs, total_execution_time_ms } sorted by runs desc
    """
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()

    pid = _pid(project_id)
    where = "project_id = ?"
    params: List[Any] = [pid]
    if start_date:
        where += " AND DATE(created_at) >= ?"
        params.append(start_date)
    if end_date:
        where += " AND DATE(created_at) <= ?"
        params.append(end_date)

    # Total runs, execution time, and total agent cost (workflow cost)
    cur.execute(
        f"""
        SELECT COUNT(*) AS total_runs,
               COALESCE(SUM(execution_time_ms), 0) AS total_execution_time_ms,
               COALESCE(SUM(agent_cost), 0) AS total_agent_cost
        FROM usage_records
        WHERE {where}
        """,
        params,
    )
    row = cur.fetchone()
    total_runs = int(row["total_runs"]) if row else 0
    total_execution_time_ms = int(row["total_execution_time_ms"]) if row else 0
    total_agent_cost = float(row["total_agent_cost"]) if row and row["total_agent_cost"] is not None else 0.0

    # Per-agent breakdown (including agent_cost for billing)
    cur.execute(
        f"""
        SELECT agent_name,
               COUNT(*) AS runs,
               COALESCE(SUM(execution_time_ms), 0) AS total_execution_time_ms,
               COALESCE(SUM(agent_cost), 0) AS total_agent_cost
        FROM usage_records
        WHERE {where}
        GROUP BY agent_name
        ORDER BY runs DESC
        """,
        params,
    )
    runs_per_agent = [
        {
            "agent_name": r["agent_name"],
            "runs": int(r["runs"]),
            "total_execution_time_ms": int(r["total_execution_time_ms"]),
            "total_agent_cost": float(r["total_agent_cost"]) if r.get("total_agent_cost") is not None else 0.0,
        }
        for r in cur.fetchall()
    ]

    # Per-day for workflow usage per day chart
    cur.execute(
        f"""
        SELECT DATE(created_at) AS date,
               COUNT(*) AS runs,
               COALESCE(SUM(execution_time_ms), 0) AS total_execution_time_ms
        FROM usage_records
        WHERE {where}
        GROUP BY DATE(created_at)
        ORDER BY date ASC
        """,
        params,
    )
    usage_per_day = [
        {
            "date": r["date"],
            "runs": int(r["runs"]),
            "total_execution_time_ms": int(r["total_execution_time_ms"]),
        }
        for r in cur.fetchall()
    ]

    return {
        "total_runs": total_runs,
        "total_execution_time_ms": total_execution_time_ms,
        "total_agent_cost": total_agent_cost,
        "runs_per_agent": runs_per_agent,
        "usage_per_day": usage_per_day,
        "top_agents": runs_per_agent[:10],
    }


def get_recent_runs_by_agent(days: int = 30) -> Dict[str, int]:
    """
    Return count of runs per agent_name in the last `days` days (from usage_records).
    Used for ranking: recent_runs in score = runs*3 + average_rating*10 + recent_runs*5.
    """
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT agent_name, COUNT(*) AS cnt
        FROM usage_records
        WHERE agent_name IS NOT NULL AND agent_name != ''
          AND created_at >= NOW() AT TIME ZONE 'UTC' - (?::interval)
        GROUP BY agent_name
        """,
        (f"{days} days",),
    )
    return {row["agent_name"]: int(row["cnt"]) for row in cur.fetchall()}


def get_usage_this_month(project_id: Union[int, uuid.UUID]) -> Dict[str, int]:
    """
    Return runs and execution_time_ms for the current calendar month (UTC).
    Used by quota checker for monthly limits.
    """
    _ensure_schema()
    cur = db.get_connection().cursor()
    pid = _pid(project_id)
    cur.execute(
        """
        SELECT COUNT(*) AS runs, COALESCE(SUM(execution_time_ms), 0) AS execution_time_ms
        FROM usage_records
        WHERE project_id = ?
          AND date_trunc('month', created_at AT TIME ZONE 'UTC') = date_trunc('month', NOW() AT TIME ZONE 'UTC')
        """,
        (pid,),
    )
    row = cur.fetchone()
    return {
        "runs_this_month": int(row["runs"]) if row else 0,
        "execution_time_this_month_ms": int(row["execution_time_ms"]) if row else 0,
    }


