from orchestrator.capability_index import get_agents_for_task


def route_task(task):
    """
    Select agents based on capability keywords using the capability index.
    """

    # Use the capability index to find matching agents for the task.
    selected_agents = get_agents_for_task(task)

    # If no agents were found, default to the research agent.
    if not selected_agents:
        selected_agents = ["research"]

    # Always ensure execution agent runs last.
    if "execution" not in selected_agents:
        selected_agents.append("execution")

    return selected_agents


def build_dag(selected_agents):
    """
    Build dependency graph dynamically.
    """

    dag = {}
    selected = set(selected_agents)

    # research has no dependencies
    if "research" in selected:
        dag["research"] = []

    # strategy depends on research if research is selected
    if "strategy" in selected:
        deps = []
        if "research" in selected:
            deps.append("research")
        dag["strategy"] = deps

    # content depends on strategy if present, otherwise research
    if "content" in selected:
        deps = []
        if "strategy" in selected:
            deps.append("strategy")
        elif "research" in selected:
            deps.append("research")
        dag["content"] = deps

    # tool depends on strategy if present, otherwise research
    if "tool" in selected:
        deps = []
        if "strategy" in selected:
            deps.append("strategy")
        elif "research" in selected:
            deps.append("research")
        dag["tool"] = deps

    # execution depends on all previous agents that exist
    if "execution" in selected:
        deps = []
        for a in ["research", "strategy", "content", "tool"]:
            if a in selected:
                deps.append(a)
        dag["execution"] = deps

    return dag