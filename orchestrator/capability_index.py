from __future__ import annotations

from typing import Dict, List

from registry.agent_registry import agent_registry


CAPABILITY_INDEX: Dict[str, List[str]] = {}


def build_index() -> Dict[str, List[str]]:
    """
    Build a global capability index mapping capability -> list of agent names.
    Uses the agents currently registered in agent_registry.
    """
    global CAPABILITY_INDEX

    index: Dict[str, List[str]] = {}

    for name, agent in agent_registry.agents.items():
        capabilities = getattr(agent, "capabilities", [])
        if not isinstance(capabilities, (list, tuple)):
            continue

        for capability in capabilities:
            if not isinstance(capability, str):
                continue

            key = capability.lower()
            agents_for_capability = index.setdefault(key, [])
            if name not in agents_for_capability:
                agents_for_capability.append(name)

    CAPABILITY_INDEX = index
    return CAPABILITY_INDEX


def _get_index() -> Dict[str, List[str]]:
    """
    Internal helper to lazily initialize the capability index if needed.
    """
    if not CAPABILITY_INDEX:
        build_index()
    return CAPABILITY_INDEX


def get_agents_for_task(task: str) -> List[str]:
    """
    Return a list of agent names whose capabilities match words in the task.

    Matching is done by checking if each capability string (lowercased) is a
    substring of the task text (also lowercased). The result list is
    de-duplicated while preserving order of first appearance.
    """
    if not task:
        return []

    task_lc = task.lower()
    index = _get_index()

    selected: List[str] = []
    seen = set()

    for capability, agents in index.items():
        if capability in task_lc:
            for agent_name in agents:
                if agent_name not in seen:
                    seen.add(agent_name)
                    selected.append(agent_name)

    return selected