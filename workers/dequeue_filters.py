"""Worker-side task filtering before Postgres claim (matches services.task_service)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _is_agent_edge_compatible(agent_name: Any) -> bool:
    if not agent_name:
        return False
    try:
        from engine.edge_routing import is_agent_edge_compatible

        return is_agent_edge_compatible(agent_name)
    except Exception:
        return False


def task_matches_worker(
    parsed: Dict[str, Any],
    *,
    worker_capabilities: Optional[List[str]] = None,
    worker_region: Optional[str] = None,
    worker_type: Optional[str] = None,
) -> bool:
    required = parsed.get("required_capabilities")
    if required and worker_capabilities is not None:
        if not all(r in worker_capabilities for r in required):
            return False

    target_region = parsed.get("target_region")
    if target_region and worker_region:
        if target_region.strip().lower() != worker_region.strip().lower():
            return False

    agent_name = parsed.get("agent")
    if worker_type and worker_type.strip().lower() == "edge":
        if not _is_agent_edge_compatible(agent_name):
            return False
    elif (worker_type or "").strip().lower() != "edge":
        if _is_agent_edge_compatible(agent_name):
            return False

    return True
