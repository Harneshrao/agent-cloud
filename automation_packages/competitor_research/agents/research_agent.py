"""Package agent: research (competitor_research). Registered as competitor_research.research_agent."""

from sdk.agent import Agent


class ResearchAgent(Agent):
    name = "research_agent"
    tools = ["web_search"]

    def run(self, state):
        task = state.get("task", "")
        return {"competitor_research_result": f"Competitor research: {task}"}
