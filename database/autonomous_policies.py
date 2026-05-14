"""
Autonomous workforce policy engine: control which agents may launch workflows,
maximum frequency, and resource limits.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from database.db import db

# source: "user" | "agent"
LAUNCH_SOURCE_AGENT = "agent"
LAUNCH_SOURCE_USER = "user"


def _ensure_schema() -> None:
    """Schema from Alembic only; no runtime DDL."""
    return


def get_policy(project_id: int, agent_name: str) -> Optional[Dict[str, Any]]:
    """Return policy for (project_id, agent_name). None means use default (allow, no limit)."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT project_id, agent_name, allowed, max_launches_per_hour, max_concurrent_workflows
        FROM autonomous_policies
        WHERE project_id = ? AND agent_name = ?
        """,
        (project_id, agent_name),
    )
    row = cur.fetchone()
    if row is None:
        return None
    return {
        "project_id": row["project_id"],
        "agent_name": row["agent_name"],
        "allowed": bool(row["allowed"]),
        "max_launches_per_hour": row["max_launches_per_hour"],
        "max_concurrent_workflows": row["max_concurrent_workflows"],
    }


def set_policy(
    project_id: int,
    agent_name: str,
    allowed: bool = True,
    max_launches_per_hour: Optional[int] = None,
    max_concurrent_workflows: Optional[int] = None,
) -> Dict[str, Any]:
    """Set or update policy for (project_id, agent_name). Use '*' for agent_name to mean any agent."""
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO autonomous_policies (project_id, agent_name, allowed, max_launches_per_hour, max_concurrent_workflows, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(project_id, agent_name) DO UPDATE SET
            allowed = excluded.allowed,
            max_launches_per_hour = excluded.max_launches_per_hour,
            max_concurrent_workflows = excluded.max_concurrent_workflows
        """,
        (project_id, agent_name, 1 if allowed else 0, max_launches_per_hour, max_concurrent_workflows, datetime.utcnow()),
    )
    conn.commit()
    return get_policy(project_id, agent_name) or {}


def _log_launch(project_id: int, agent_name: str, source: str) -> None:
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO autonomous_launch_log (project_id, agent_name, source, created_at) VALUES (?, ?, ?, ?)",
        (project_id, agent_name, source, datetime.utcnow()),
    )
    conn.commit()


def _count_launches_last_hour(project_id: int, agent_name: str) -> int:
    _ensure_schema()
    cur = db.get_connection().cursor()
    since = datetime.utcnow() - timedelta(hours=1)
    cur.execute(
        """
        SELECT COUNT(*) AS n FROM autonomous_launch_log
        WHERE project_id = ? AND agent_name = ? AND created_at >= ?
        """,
        (project_id, agent_name, since),
    )
    row = cur.fetchone()
    return row["n"] if row else 0


def can_agent_launch_workflow(
    agent_name: str,
    project_id: int,
    source: str = LAUNCH_SOURCE_AGENT,
) -> bool:
    """
    Return True if this agent is allowed to launch a workflow in this project.
    Checks policy (allowlist) and rate limit (max_launches_per_hour).
    """
    _ensure_schema()
    policy = get_policy(project_id, agent_name)
    if policy is None:
        policy = get_policy(project_id, "*")
    if policy is not None and not policy.get("allowed", True):
        return False
    max_per_hour = (policy or {}).get("max_launches_per_hour")
    if max_per_hour is not None:
        count = _count_launches_last_hour(project_id, agent_name)
        if count >= max_per_hour:
            return False
    return True


def record_launch_and_check(
    agent_name: str,
    project_id: int,
    source: str = LAUNCH_SOURCE_AGENT,
) -> bool:
    """
    Record a launch and return True if it was allowed (policy + rate limit).
    Call this just before enqueueing; if False, do not enqueue.
    """
    if not can_agent_launch_workflow(agent_name, project_id, source):
        return False
    _log_launch(project_id, agent_name, source)
    return True


def list_policies_for_project(project_id: int) -> List[Dict[str, Any]]:
    """List all policies for a project."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT project_id, agent_name, allowed, max_launches_per_hour, max_concurrent_workflows
        FROM autonomous_policies
        WHERE project_id = ?
        ORDER BY agent_name
        """,
        (project_id,),
    )
    return [
        {
            "project_id": r["project_id"],
            "agent_name": r["agent_name"],
            "allowed": bool(r["allowed"]),
            "max_launches_per_hour": r["max_launches_per_hour"],
            "max_concurrent_workflows": r["max_concurrent_workflows"],
        }
        for r in cur.fetchall()
    ]
