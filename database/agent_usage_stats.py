"""
Agent usage statistics aggregated from usage_records.

Table: agent_usage_stats (agent_name PRIMARY KEY, runs, avg_execution_time, last_used_at)
Refreshed from usage_records for ranking and discovery.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from database.db import db


def _ensure_schema() -> None:
    """Schema from Alembic only; no runtime DDL."""
    return


def increment_agent_run(agent_name: str) -> None:
    """Increment runs and set last_used_at after each agent execution."""
    if not agent_name or not str(agent_name).strip():
        return
    _ensure_schema()
    from datetime import datetime
    conn = db.get_connection()
    cur = conn.cursor()
    now = datetime.utcnow()
    cur.execute(
        """
        INSERT INTO agent_usage_stats (agent_name, runs, avg_execution_time, last_used_at)
        VALUES (?, 1, 0, ?)
        ON CONFLICT(agent_name) DO UPDATE SET
            runs = runs + 1,
            last_used_at = excluded.last_used_at
        """,
        (agent_name.strip(), now),
    )
    conn.commit()


def refresh_from_usage_records() -> None:
    """Aggregate usage_records by agent_name and upsert into agent_usage_stats."""
    _ensure_schema()
    # Ensure usage_records table exists
    try:
        from database.usage_records import _ensure_schema as ur_ensure
        ur_ensure()
    except Exception:
        pass
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO agent_usage_stats (agent_name, runs, avg_execution_time, last_used_at)
        SELECT
            agent_name,
            COUNT(*) AS runs,
            COALESCE(AVG(execution_time_ms), 0) AS avg_execution_time,
            MAX(created_at) AS last_used_at
        FROM usage_records
        WHERE agent_name IS NOT NULL AND agent_name != ''
        GROUP BY agent_name
        ON CONFLICT (agent_name) DO UPDATE SET
            runs = EXCLUDED.runs,
            avg_execution_time = EXCLUDED.avg_execution_time,
            last_used_at = EXCLUDED.last_used_at
        """
    )
    conn.commit()


def get_stats_for_agent(agent_name: str) -> Optional[Dict[str, Any]]:
    """Return usage stats for one agent, or None."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT agent_name, runs, avg_execution_time, last_used_at
        FROM agent_usage_stats
        WHERE agent_name = ?
        """,
        (agent_name,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    last = row["last_used_at"]
    if hasattr(last, "isoformat"):
        last = last.isoformat()
    return {
        "agent_name": row["agent_name"],
        "runs": int(row["runs"]),
        "avg_execution_time": float(row["avg_execution_time"]),
        "last_used_at": last,
    }


def get_all_stats() -> List[Dict[str, Any]]:
    """Return all agent_usage_stats rows."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT agent_name, runs, avg_execution_time, last_used_at
        FROM agent_usage_stats
        ORDER BY runs DESC
        """
    )
    out = []
    for row in cur.fetchall():
        last = row["last_used_at"]
        if hasattr(last, "isoformat"):
            last = last.isoformat()
        out.append({
            "agent_name": row["agent_name"],
            "runs": int(row["runs"]),
            "avg_execution_time": float(row["avg_execution_time"]),
            "last_used_at": last,
        })
    return out
