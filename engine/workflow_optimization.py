"""
Autonomous workflow optimization: identify slow nodes, generate recommendations,
and optionally apply DAG modifications for performance.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from database.workflow_analytics import (
    get_aggregate_workflow_metrics,
    get_slow_nodes,
    get_workflow_run_metrics,
)
from database.workflow_nodes import get_nodes
from database.workflow_templates import get_template_by_id
from database.template_versions import get_latest_version, resolve_dag_for_run


def _topological_order(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return nodes in topological order (deps before dependents)."""
    result: List[Dict[str, Any]] = []
    added: set = set()
    nodes = list(nodes)
    result_ids = set()
    while len(result) < len(nodes):
        layer = [
            n for n in nodes
            if (n.get("id") or "") not in result_ids
            and all(d in added for d in (n.get("deps") or []))
        ]
        if not layer:
            break
        for n in layer:
            result.append(n)
            kid = n.get("id")
            if kid is not None:
                added.add(kid)
                result_ids.add(kid)
    for n in nodes:
        if (n.get("id") or "") not in result_ids:
            result.append(n)
    return result


def identify_slow_nodes(
    window_days: int = 30,
    min_runs: int = 3,
    top_n: int = 10,
) -> List[Dict[str, Any]]:
    """
    Identify the slowest workflow nodes (by agent). Returns list of
    { agent_name, runs, average_runtime_ms, total_execution_time_ms, failure_rate }
    sorted by average_runtime_ms descending.
    """
    return get_slow_nodes(window_days=window_days, min_runs=min_runs, top_n=top_n)


def generate_recommendations(
    template_id: Optional[int] = None,
    workflow_id: Optional[int] = None,
    window_days: int = 30,
) -> List[Dict[str, Any]]:
    """
    Suggest improvements: parallelize nodes, change agent order, increase worker resources.
    Each recommendation: { id, type, title, description, agent_name?, node_id?, params?, impact }
    """
    recommendations: List[Dict[str, Any]] = []
    slow = identify_slow_nodes(window_days=window_days, top_n=5)
    if not slow:
        return recommendations
    for i, node in enumerate(slow):
        agent_name = node.get("agent_name", "unknown")
        avg_ms = node.get("average_runtime_ms", 0)
        rec_id = f"slow_node_{i}_{agent_name}"
        recommendations.append({
            "id": rec_id,
            "type": "increase_worker_resources",
            "title": f"Scale resources for slow agent: {agent_name}",
            "description": f"{agent_name} has average runtime {avg_ms:.0f}ms. Assign more workers or higher capability workers for this agent to reduce latency.",
            "agent_name": agent_name,
            "params": {"average_runtime_ms": avg_ms},
            "impact": "high",
        })
    agg = get_aggregate_workflow_metrics(window_days=window_days, template_id=template_id)
    by_agent = agg.get("by_agent", [])
    if len(by_agent) >= 2:
        ordered = sorted(by_agent, key=lambda x: x.get("average_runtime_ms", 0))
        fastest = ordered[0].get("agent_name")
        slowest = ordered[-1].get("agent_name")
        if fastest and slowest and fastest != slowest:
            recommendations.append({
                "id": "reorder_agents",
                "type": "change_agent_order",
                "title": "Run faster agents earlier where dependencies allow",
                "description": f"Consider moving '{fastest}' (faster) before '{slowest}' in the DAG where dependency order permits to improve perceived latency.",
                "agent_name": None,
                "params": {"fastest": fastest, "slowest": slowest},
                "impact": "medium",
            })
    if workflow_id is not None:
        nodes = get_nodes(workflow_id)
        roots = [n for n in nodes if not (n.get("deps") or [])]
        if len(roots) >= 2:
            recommendations.append({
                "id": "parallelize_root",
                "type": "parallelize_nodes",
                "title": "Root nodes can run in parallel",
                "description": f"Workflow has {len(roots)} root nodes with no dependencies; they are already parallelizable. Ensure enough workers to run them concurrently.",
                "node_id": [n.get("node_id") for n in roots],
                "params": {"root_count": len(roots)},
                "impact": "medium",
            })
        else:
            independent = []
            for n in nodes:
                deps = n.get("deps") or []
                for other in nodes:
                    if other["node_id"] == n["node_id"]:
                        continue
                    if other["node_id"] in deps or n["node_id"] in (other.get("deps") or []):
                        continue
                    independent.append((n["node_id"], other["node_id"]))
            if independent:
                recommendations.append({
                    "id": "parallelize_independent",
                    "type": "parallelize_nodes",
                    "title": "Independent nodes can run in parallel",
                    "description": "Some node pairs have no dependency; ensure DAG allows parallel execution and sufficient workers.",
                    "params": {},
                    "impact": "low",
                })
    return recommendations


def get_optimization_summary(
    template_id: Optional[int] = None,
    window_days: int = 30,
) -> Dict[str, Any]:
    """Return slow nodes plus recommendations for dashboards."""
    slow = identify_slow_nodes(window_days=window_days)
    recommendations = generate_recommendations(template_id=template_id, window_days=window_days)
    agg = get_aggregate_workflow_metrics(window_days=window_days, template_id=template_id)
    return {
        "slow_nodes": slow,
        "recommendations": recommendations,
        "aggregate_metrics": {
            "workflow_runs": agg.get("workflow_runs", 0),
            "average_runtime_ms": agg.get("average_runtime_ms", 0),
            "failure_rate": agg.get("failure_rate", 0),
        },
    }


def apply_optimization(
    template_id: int,
    recommendation_id: str,
    dry_run: bool = True,
) -> Dict[str, Any]:
    """
    (Optional) Apply a recommendation to a workflow template's DAG.
    Currently supports no structural changes; returns summary of what would change.
    When dry_run=False, can update template version DAG (e.g. reorder nodes) if implemented.
    """
    template = get_template_by_id(template_id)
    if template is None:
        return {"ok": False, "error": f"Template {template_id} not found"}
    dag = resolve_dag_for_run(template_id)
    if not dag:
        dag = template.get("dag_definition") or {}
    nodes = dag.get("nodes") if isinstance(dag, dict) else []
    if not nodes:
        return {"ok": False, "error": "Template has no DAG nodes"}
    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "template_id": template_id,
            "recommendation_id": recommendation_id,
            "message": "Dry run: set dry_run=false to apply reorder_agents or other optimizations.",
            "current_nodes": [n.get("id") for n in nodes],
        }
    if recommendation_id == "reorder_agents":
        agg = get_aggregate_workflow_metrics(window_days=30, template_id=template_id)
        by_agent = {x["agent_name"]: x.get("average_runtime_ms", 0) for x in agg.get("by_agent", [])}

        def avg_ms(n: Dict[str, Any]) -> float:
            return by_agent.get(n.get("agent") or n.get("agent_name") or "", float("inf"))

        topo = _topological_order(nodes)
        within_layer: List[Dict[str, Any]] = []
        reordered: List[Dict[str, Any]] = []
        prev_deps: Optional[set] = None
        for n in topo:
            deps = set(n.get("deps") or [])
            if prev_deps is not None and deps != prev_deps:
                within_layer.sort(key=avg_ms)
                reordered.extend(within_layer)
                within_layer = []
            within_layer.append(n)
            prev_deps = deps
        if within_layer:
            within_layer.sort(key=avg_ms)
            reordered.extend(within_layer)
        new_dag = {**dag, "nodes": reordered}
        try:
            from datetime import datetime
            from database.template_versions import create_version
            version_label = "opt-" + datetime.utcnow().strftime("%Y%m%d-%H%M%S")
            create_version(template_id, version_label, new_dag)
            return {
                "ok": True,
                "dry_run": False,
                "template_id": template_id,
                "recommendation_id": recommendation_id,
                "message": "Created new template version with nodes reordered by agent speed.",
                "previous_order": [n.get("id") for n in nodes],
                "new_order": [n.get("id") for n in reordered],
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}
    return {
        "ok": True,
        "dry_run": False,
        "template_id": template_id,
        "recommendation_id": recommendation_id,
        "message": "No automatic change for this recommendation.",
        "current_nodes": [n.get("id") for n in nodes],
    }
