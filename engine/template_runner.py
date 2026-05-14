"""
Template execution: parse dag_definition, create tasks per node, link in task_graph.

Reuses existing DB task creation and task_graph; does not modify workflow engine,
task queue, sandbox, or workers. Creates one task per node and records parent-child
links so the workflow can be observed. Workers pick pending tasks; execution order
may not follow the DAG unless the queue respects dependencies.
"""

from __future__ import annotations

import json
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple

from database.db import db
from database.task_graph import insert_link
from database.template_versions import resolve_dag_for_run
from database.workflow_templates import get_template_by_id, record_template_run


def merge_template_inputs(
    install_config: Optional[Dict[str, Any]],
    runtime_inputs: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """
    Merge install config with runtime inputs for template execution.
    Runtime inputs override install config values. Returns None if both are empty/None.
    """
    config = (install_config or {}) if isinstance(install_config, dict) else {}
    runtime = (runtime_inputs or {}) if isinstance(runtime_inputs, dict) else {}
    if not config and not runtime:
        return None
    return {**config, **runtime}


def _substitute_inputs(text: str, inputs: Dict[str, Any]) -> str:
    """Replace {{key}} in text with inputs.get(key, ''). Keys are word characters."""
    if not text or not inputs:
        return text
    return re.sub(
        r"\{\{(\w+)\}\}",
        lambda m: str(inputs.get(m.group(1), "")),
        text,
    )


def _parse_dag(dag_definition: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Expects dag_definition with "nodes": [ {"id": "n1", "agent": "...", "task": "..."}, {"id": "n2", "deps": ["n1"], ...} ].
    Returns list of nodes with "id", "agent", "task", "deps" (optional).
    """
    nodes = dag_definition.get("nodes") if isinstance(dag_definition, dict) else None
    if not nodes or not isinstance(nodes, list):
        return []
    out = []
    for n in nodes:
        if not isinstance(n, dict):
            continue
        node_id = n.get("id") or str(len(out))
        agent = n.get("agent")
        task = n.get("task") or ""
        deps = n.get("deps")
        if deps is not None and not isinstance(deps, list):
            deps = []
        out.append({"id": node_id, "agent": agent, "task": task, "deps": deps or []})
    return out


def run_template(
    template_id: int,
    project_id: uuid.UUID,
    task_override: Optional[str] = None,
    version: Optional[str] = None,
    inputs: Optional[Dict[str, Any]] = None,
) -> Tuple[List[uuid.UUID], List[uuid.UUID]]:
    """
    Load template, resolve DAG, substitute {{key}} in node tasks with inputs, create tasks.
    inputs: optional dict for parameter substitution; if template has no input_schema, substitution is still applied when inputs is provided.
    Returns (root_task_ids, all_task_ids). Records template run (run_count, last_run_at).
    """
    template = get_template_by_id(template_id)
    if template is None:
        raise ValueError(f"Template {template_id} not found")
    dag = resolve_dag_for_run(template_id, version=version)
    if dag is None:
        dag = template.get("dag_definition") or {}
    subs = inputs if inputs and isinstance(inputs, dict) else {}
    nodes = _parse_dag(dag)
    if not nodes:
        # Fallback: single task using template description
        task_text = task_override or template.get("description") or f"Run template: {template.get('name', '')}"
        task_text = _substitute_inputs(task_text, subs)
        payload = {"task": task_text, "agent": None}
        task_id = db.create_task(
            task_text=json.dumps(payload),
            status="queued",
            project_id=project_id,
        )
        record_template_run(template_id)
        return ([task_id], [task_id])

    node_id_to_task_id: Dict[str, uuid.UUID] = {}
    for node in nodes:
        task_str = node.get("task") or ""
        agent = node.get("agent")
        if task_override and not node.get("deps"):
            task_str = task_override
        task_str = _substitute_inputs(task_str, subs)
        payload = {"task": task_str, "agent": agent}
        task_text = json.dumps(payload)
        tid = db.create_task(task_text=task_text, status="queued", project_id=project_id)
        node_id_to_task_id[node["id"]] = tid

    for node in nodes:
        tid = node_id_to_task_id.get(node["id"])
        if tid is None:
            continue
        for dep_id in node.get("deps") or []:
            parent_tid = node_id_to_task_id.get(dep_id)
            if parent_tid is not None:
                insert_link(task_id=tid, parent_task_id=parent_tid, status="pending")

    root_ids = [
        node_id_to_task_id[n["id"]]
        for n in nodes
        if not (n.get("deps"))
    ]
    if not root_ids:
        root_ids = list(node_id_to_task_id.values())[:1]
    all_ids = list(node_id_to_task_id.values())
    record_template_run(template_id)
    return (root_ids, all_ids)
