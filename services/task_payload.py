"""Serialize / parse task payloads stored in tasks.task_text (JSON)."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional, Union


def serialize_payload(payload: Union[str, Dict[str, Any]]) -> str:
    if isinstance(payload, dict):
        return json.dumps(payload)
    return str(payload)


def parse_payload(task_text: Any) -> Dict[str, Any]:
    if task_text is None:
        return {"task": "", "agent": None}
    s = str(task_text).strip()
    if not s:
        return {"task": "", "agent": None}
    if s.startswith("{"):
        try:
            data = json.loads(s)
            out: Dict[str, Any] = {
                "task": data.get("task", ""),
                "agent": data.get("agent"),
            }
            if "runtime" in data and data["runtime"]:
                out["runtime"] = data["runtime"]
            if "workflow_id" in data:
                out["workflow_id"] = data["workflow_id"]
            if "node_id" in data:
                out["node_id"] = data["node_id"]
            if "deps" in data:
                out["deps"] = data["deps"]
            if "required_capabilities" in data and isinstance(data["required_capabilities"], list):
                out["required_capabilities"] = data["required_capabilities"]
            if "priority" in data and isinstance(data["priority"], (int, float)):
                out["priority"] = int(data["priority"])
            if "idempotency_key" in data and data["idempotency_key"]:
                out["idempotency_key"] = data["idempotency_key"]
            if "target_region" in data and data["target_region"]:
                out["target_region"] = data["target_region"]
            if "agent_instance_id" in data and data["agent_instance_id"]:
                out["agent_instance_id"] = data["agent_instance_id"]
            if "installation_id" in data and data["installation_id"] is not None:
                out["installation_id"] = data["installation_id"]
            if "input" in data:
                out["input"] = data["input"]
            return out
        except (json.JSONDecodeError, TypeError):
            pass
    return {"task": s, "agent": None}


def get_agent_capabilities(agent_name: Any) -> list:
    if not agent_name:
        return []
    try:
        from registry.agent_registry import agent_registry

        agent = agent_registry.get_agent(agent_name)
        if agent is not None and hasattr(agent, "capabilities"):
            caps = getattr(agent, "capabilities", None)
            if isinstance(caps, (list, tuple)):
                return [str(c) for c in caps]
    except Exception:
        pass
    return []


def ensure_task_capabilities(payload: Dict[str, Any]) -> Dict[str, Any]:
    if payload.get("required_capabilities"):
        return payload
    caps = get_agent_capabilities(payload.get("agent"))
    if caps:
        payload = dict(payload)
        payload["required_capabilities"] = caps
    return payload
