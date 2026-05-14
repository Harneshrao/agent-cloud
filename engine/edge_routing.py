"""
Edge execution: determine if an agent is eligible to run on edge workers.
"""


def is_agent_edge_compatible(agent_name: str | None) -> bool:
    """
    Return True if the agent is registered and has edge_compatible == True.
    Unknown or missing agents are treated as not edge-compatible (cloud only).
    """
    if not agent_name:
        return False
    try:
        from registry.agent_registry import agent_registry
        agent = agent_registry.get_agent(agent_name)
        if agent is None:
            return False
        return bool(getattr(agent, "edge_compatible", False))
    except Exception:
        return False
