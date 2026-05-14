"""Package agent: research. Behaves like a normal platform agent."""

from sdk.agent import Agent


class ResearchAgent(Agent):
    name = "research_agent"
    tools = ["web_search"]

    def run(self, state):
        task = state.get("task", "")
        return {"research_result": f"Researched: {task}"}
