"""
Workflow analytics: aggregate metrics per workflow run and per node/agent.

Uses workflow_nodes (workflow_id, node_id, task_id, agent_name), usage_records
(task_id, execution_time_ms, tokens_used), and tasks (status) to compute
average runtime, failure rate, and resource usage per workflow and per agent.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from database.db import db
from database.workflow_nodes import get_nodes


def _ensure_schema() -> None:
    """No new table required; we query workflow_nodes, usage_records, tasks."""
    pass


def get_workflow_run_metrics(workflow_id: int) -> Optional[Dict[str, Any]]:
    """
    Return metrics for a single workflow run: average_runtime_ms, failure_rate,
    total_runtime_ms, resource_usage (execution_time_ms sum, tokens sum), node_metrics list.
    Returns None if workflow has no nodes or no usage data.
    """
    nodes = get_nodes(workflow_id)
    if not nodes:
        return None
    task_ids = [n["task_id"] for n in nodes if n.get("task_id") is not None]
    if not task_ids:
        return None
    conn = db.get_connection()
    cur = conn.cursor()
    placeholders = ",".join("?" * len(task_ids))
    cur.execute(
        f"""
        SELECT task_id, agent_name, execution_time_ms, COALESCE(tokens_used, 0) AS tokens_used
        FROM usage_records
        WHERE task_id IN ({placeholders})
        """,
        task_ids,
    )
    usage_by_task: Dict[int, Dict[str, Any]] = {}
    for row in cur.fetchall() or []:
        usage_by_task[row["task_id"]] = {
            "execution_time_ms": row["execution_time_ms"] or 0,
            "tokens_used": row["tokens_used"] or 0,
        }
    cur.execute(
        f"SELECT id, status FROM tasks WHERE id IN ({placeholders})",
        task_ids,
    )
    status_by_task = {row["id"]: row["status"] for row in cur.fetchall() or []}
    node_metrics: List[Dict[str, Any]] = []
    total_ms = 0
    total_tokens = 0
    completed = 0
    failed = 0
    for n in nodes:
        tid = n.get("task_id")
        if tid is None:
            continue
        status = status_by_task.get(tid, "pending")
        usage = usage_by_task.get(tid, {})
        runtime = usage.get("execution_time_ms", 0)
        tokens = usage.get("tokens_used", 0)
        total_ms += runtime
        total_tokens += tokens
        if status == "completed":
            completed += 1
        elif status == "failed":
            failed += 1
        node_metrics.append({
            "node_id": n.get("node_id"),
            "agent_name": n.get("agent_name"),
            "task_id": tid,
            "status": status,
            "execution_time_ms": runtime,
            "tokens_used": tokens,
        })
    num_nodes = len(node_metrics)
    if num_nodes == 0:
        return None
    return {
        "workflow_id": workflow_id,
        "average_runtime_ms": round(total_ms / num_nodes, 2),
        "total_runtime_ms": total_ms,
        "failure_rate": round(failed / num_nodes, 4),
        "completed_nodes": completed,
        "failed_nodes": failed,
        "total_nodes": num_nodes,
        "resource_usage": {
            "execution_time_ms": total_ms,
            "tokens_used": total_tokens,
        },
        "node_metrics": node_metrics,
    }


def get_aggregate_workflow_metrics(
    window_days: int = 30,
    template_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Aggregate metrics across workflow runs (from workflow_nodes + usage_records + tasks).
    If template_id is set, filter by root task's task_text containing that template (optional).
    Returns: runs, average_runtime_ms, failure_rate, total_execution_time_ms, by_agent.
    """
    conn = db.get_connection()
    cur = conn.cursor()
    since = datetime.utcnow() - timedelta(days=window_days)
    cur.execute(
        """
        SELECT wn.workflow_id, wn.node_id, wn.task_id, wn.agent_name,
               ur.execution_time_ms, ur.tokens_used,
               t.status
        FROM workflow_nodes wn
        LEFT JOIN usage_records ur ON wn.task_id = ur.task_id
        LEFT JOIN tasks t ON wn.task_id = t.id
        WHERE wn.task_id IS NOT NULL
        AND (t.created_at IS NULL OR t.created_at >= ?)
        """,
        (since,),
    )
    rows = cur.fetchall() or []
    if template_id is not None:
        workflow_ids = set()
        for r in rows:
            workflow_ids.add(r["workflow_id"])
        if workflow_ids:
            placeholders = ",".join("?" * len(workflow_ids))
            cur.execute(
                f"SELECT id, task_text FROM tasks WHERE id IN ({placeholders})",
                list(workflow_ids),
            )
            root_tasks = {row["id"]: row.get("task_text") or "" for row in cur.fetchall() or []}
            keep_wids = {
                wid for wid, text in root_tasks.items()
                if text and f'"template_id": {template_id}' in text
            }
            rows = [r for r in rows if r["workflow_id"] in keep_wids]
    by_workflow: Dict[int, List[Dict[str, Any]]] = {}
    by_agent: Dict[str, List[Dict[str, Any]]] = {}
    for r in rows:
        wid = r["workflow_id"]
        by_workflow.setdefault(wid, []).append(r)
        agent = r.get("agent_name") or "unknown"
        by_agent.setdefault(agent, []).append(r)
    total_runs = len(by_workflow)
    all_runtimes: List[int] = []
    all_failed = 0
    all_completed = 0
    total_execution_ms = 0
    for r in rows:
        ms = r.get("execution_time_ms") or 0
        if ms:
            all_runtimes.append(ms)
        total_execution_ms += ms
        if r.get("status") == "failed":
            all_failed += 1
        elif r.get("status") == "completed":
            all_completed += 1
    total_outcomes = all_completed + all_failed
    failure_rate = (all_failed / total_outcomes) if total_outcomes else 0.0
    avg_runtime = (sum(all_runtimes) / len(all_runtimes)) if all_runtimes else 0
    agent_stats: List[Dict[str, Any]] = []
    for agent_name, agent_rows in by_agent.items():
        runtimes = [x.get("execution_time_ms") or 0 for x in agent_rows if x.get("execution_time_ms")]
        failed = sum(1 for x in agent_rows if x.get("status") == "failed")
        completed = sum(1 for x in agent_rows if x.get("status") == "completed")
        agent_stats.append({
            "agent_name": agent_name,
            "runs": len(agent_rows),
            "average_runtime_ms": round(sum(runtimes) / len(runtimes), 2) if runtimes else 0,
            "total_execution_time_ms": sum(runtimes),
            "failure_rate": round(failed / (completed + failed), 4) if (completed + failed) else 0,
        })
    agent_stats.sort(key=lambda x: x["average_runtime_ms"], reverse=True)
    return {
        "window_days": window_days,
        "template_id": template_id,
        "workflow_runs": total_runs,
        "average_runtime_ms": round(avg_runtime, 2),
        "failure_rate": round(failure_rate, 4),
        "total_execution_time_ms": total_execution_ms,
        "by_agent": agent_stats,
    }


def get_slow_nodes(
    window_days: int = 30,
    min_runs: int = 3,
    top_n: int = 10,
) -> List[Dict[str, Any]]:
    """
    Return the slowest workflow nodes (by agent) by average runtime.
    Only includes agents with at least min_runs in the window.
    """
    agg = get_aggregate_workflow_metrics(window_days=window_days)
    by_agent = agg.get("by_agent", [])
    candidates = [a for a in by_agent if a.get("runs", 0) >= min_runs]
    candidates.sort(key=lambda x: x.get("average_runtime_ms", 0), reverse=True)
    return candidates[:top_n]
