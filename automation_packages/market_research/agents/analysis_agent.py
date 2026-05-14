"""Package agent: analysis. Behaves like a normal platform agent."""

from sdk.agent import Agent


class AnalysisAgent(Agent):
    name = "analysis_agent"
    tools = []

    def run(self, state):
        prev = state.get("research_result", "")
        return {"analysis_result": f"Analysis of: {prev}"}
