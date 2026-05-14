"""
Distributed DAG execution: track node dependencies, enqueue ready nodes, update workflow progress.

Each DAG node becomes a separate task. Workers run one node per task; when a node completes,
the scheduler enqueues nodes whose dependencies are satisfied. When all nodes complete,
the workflow is marked completed and the final result is stored.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional, Tuple

from database.db import db
from database.workflow_nodes import (
    all_nodes_completed,
    get_dependents,
    get_node_status,
    get_nodes,
    insert_nodes,
    set_node_status,
    set_node_task_id,
)
from database.workflow_checkpoints import (
    checkpoint_status,
    get_all_checkpoints,
    initialize_workflow,
    set_completed as checkpoint_set_completed,
    set_failed as checkpoint_set_failed,
)
from database.workflow_templates import get_template_by_id, record_template_run
from database.template_versions import resolve_dag_for_run

from engine.template_runner import _parse_dag, _substitute_inputs

try:
    from task_queue.redis_queue import push_existing_task as _enqueue_existing_task
except Exception:
    def _enqueue_existing_task(_tid: uuid.UUID, _text: str) -> None:
        pass  # DB queue: task already pending


def _get_agent_capabilities(agent_name: str) -> List[str]:
    """Return required_capabilities from agent registry if agent has .capabilities."""
    if not agent_name:
        return []
    try:
        from registry.agent_registry import agent_registry
        agent = agent_registry.get_agent(agent_name)
        if agent is not None and hasattr(agent, "capabilities") and isinstance(getattr(agent, "capabilities", None), (list, tuple)):
            return [str(c) for c in getattr(agent, "capabilities")]
    except Exception:
        pass
    return []


def _parse_dag_from_template(template_id: int, version: Optional[str]) -> List[Dict[str, Any]]:
    """Resolve DAG for template and return parsed nodes."""
    template = get_template_by_id(template_id)
    if template is None:
        return []
    dag = resolve_dag_for_run(template_id, version=version)
    if dag is None:
        dag = template.get("dag_definition") or {}
    return _parse_dag(dag)


def start_distributed_workflow(
    template_id: int,
    project_id: uuid.UUID,
    inputs: Optional[Dict[str, Any]] = None,
    task_override: Optional[str] = None,
    version: Optional[str] = None,
) -> Tuple[uuid.UUID, List[uuid.UUID]]:
    """
    Start a distributed workflow: create workflow root task, one DB task per DAG node,
    track nodes in workflow_nodes, enqueue only root nodes (deps=[]).
    Returns (workflow_id, list of enqueued root task_ids).
    """
    template = get_template_by_id(template_id)
    if template is None:
        raise ValueError(f"Template {template_id} not found")
    nodes = _parse_dag_from_template(template_id, version)
    if not nodes:
        raise ValueError("Template has no DAG nodes")
    subs = inputs if isinstance(inputs, dict) else {}
    # Workflow root task (placeholder for workflow_id). Use status 'workflow_root' so workers never fetch it.
    workflow_id = db.create_task(
        task_text=json.dumps({"type": "workflow_root", "template_id": template_id}),
        status="workflow_root",
        project_id=project_id,
    )
    nodes_with_task = [
        {**n, "task": _substitute_inputs(n.get("task") or "", subs)}
        for n in nodes
    ]
    insert_nodes(workflow_id, nodes_with_task)
    initialize_workflow(workflow_id, [n.get("id") or "" for n in nodes_with_task])
    record_template_run(template_id)
    enqueued: List[uuid.UUID] = []
    for node in nodes_with_task:
        if node.get("deps"):
            continue
        node_id = node.get("id") or ""
        agent_name = node.get("agent") or ""
        task_str = node.get("task") or ""
        if task_override:
            task_str = task_override
        payload = {
            "task": task_str,
            "agent": agent_name,
            "workflow_id": str(workflow_id),
            "node_id": node_id,
            "deps": node.get("deps") or [],
        }
        caps = _get_agent_capabilities(agent_name)
        if caps:
            payload["required_capabilities"] = caps
        task_text = json.dumps(payload)
        task_id = db.create_task(task_text=task_text, status="queued", project_id=project_id)
        set_node_task_id(workflow_id, node_id, task_id)
        _enqueue_existing_task(task_id, task_text)
        enqueued.append(task_id)
    return (workflow_id, enqueued)


def on_node_completed(
    workflow_id: uuid.UUID,
    node_id: str,
    task_id: uuid.UUID,
    agent_name: str,
    result: Any,
) -> None:
    """
    Mark node completed, store agent run, enqueue ready dependents, and mark workflow
    completed when all nodes are done (storing final result).
    """
    set_node_status(workflow_id, node_id, "completed")
    checkpoint_set_completed(workflow_id, node_id, result)
    db.store_agent_run(task_id, agent_name, result)
    # Find nodes that depend on this one and enqueue them if all their deps are completed
    dependents = get_dependents(workflow_id, node_id)
    all_nodes = get_nodes(workflow_id)
    node_by_id = {n["node_id"]: n for n in all_nodes}
    for dep in dependents:
        dep_node_id = dep["node_id"]
        if checkpoint_status(workflow_id, dep_node_id) == "completed":
            continue  # skip already completed (resume-safe)
        if dep.get("task_id") is not None:
            continue  # already enqueued
        deps_list = dep.get("deps") or []
        if not all(get_node_status(workflow_id, d) == "completed" for d in deps_list):
            continue
        node_spec = node_by_id.get(dep_node_id, dep)
        agent_name = node_spec.get("agent_name") or dep.get("agent_name") or ""
        task_str = node_spec.get("task_text") or node_spec.get("task") or ""
        payload = {
            "task": task_str,
            "agent": agent_name,
            "workflow_id": str(workflow_id),
            "node_id": dep_node_id,
            "deps": deps_list,
        }
        caps = _get_agent_capabilities(agent_name)
        if caps:
            payload["required_capabilities"] = caps
        task_text = json.dumps(payload)
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT project_id FROM tasks WHERE id = ?", (str(workflow_id),))
        row = cur.fetchone()
        project_id = row["project_id"] if row and row.get("project_id") is not None else None
        new_task_id = db.create_task(
            task_text=task_text,
            status="queued",
            project_id=project_id,
        )
        set_node_task_id(workflow_id, dep_node_id, new_task_id)
        _enqueue_existing_task(new_task_id, task_text)
    if all_nodes_completed(workflow_id):
        db.update_task_status(workflow_id, "completed")
        db.store_result(workflow_id, result)


def on_node_failed(
    workflow_id: uuid.UUID, node_id: str, task_id: uuid.UUID, error: Any
) -> None:
    """Mark node failed. Checkpoint status becomes failed; DAG scheduler may retry."""
    set_node_status(workflow_id, node_id, "failed")
    checkpoint_set_failed(workflow_id, node_id)
    db.store_agent_run(task_id, node_id, {"error": str(error)})


def resume_workflow(workflow_id: uuid.UUID) -> List[uuid.UUID]:
    """
    Resume a workflow after crash/restart: load checkpoints, enqueue only nodes
    whose status is pending or failed and whose dependencies are all completed.
    Returns list of newly enqueued task_ids.
    """
    nodes = get_nodes(workflow_id)
    if not nodes:
        return []
    checkpoints = {cp["node_id"]: cp["status"] for cp in get_all_checkpoints(workflow_id)}
    enqueued: List[uuid.UUID] = []
    node_by_id = {n["node_id"]: n for n in nodes}
    for node in nodes:
        node_id = node["node_id"]
        status = checkpoints.get(node_id, "pending")
        if status not in ("pending", "failed"):
            continue
        deps_list = node.get("deps") or []
        if not all(checkpoints.get(d) == "completed" for d in deps_list):
            continue
        if status == "pending" and node.get("task_id") is not None:
            continue  # already enqueued
        agent_name = node.get("agent_name") or ""
        task_str = node.get("task_text") or node.get("task") or ""
        payload = {
            "task": task_str,
            "agent": agent_name,
            "workflow_id": str(workflow_id),
            "node_id": node_id,
            "deps": deps_list,
        }
        caps = _get_agent_capabilities(agent_name)
        if caps:
            payload["required_capabilities"] = caps
        task_text = json.dumps(payload)
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT project_id FROM tasks WHERE id = ?", (str(workflow_id),))
        row = cur.fetchone()
        project_id = row["project_id"] if row and row.get("project_id") is not None else None
        new_task_id = db.create_task(task_text=task_text, status="queued", project_id=project_id)
        set_node_task_id(workflow_id, node_id, new_task_id)
        _enqueue_existing_task(new_task_id, task_text)
        enqueued.append(new_task_id)
    return enqueued
