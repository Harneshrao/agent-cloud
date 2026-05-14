from sdk.agent import Agent


class StrategyAgent(Agent):

    name = "strategy"
    description = "Creates business or execution strategies based on research"
    version = "1.1"

    # Capabilities used by capability routing
    capabilities = [
        "strategy",
        "planning",
        "business",
        "growth",
        "go-to-market",
        "launch"
    ]

    tools = []

    def run(self, state):

        research_data = state.get("research")
        insights = state.get("insights")

        print("🧠 Strategy Agent planning")

        strategy_plan = f"""
Strategy Plan

Research Input:
{research_data}

Key Insights:
{insights}

Recommended Strategy

1. Identify the most promising market segment
2. Define a strong value proposition
3. Develop a go-to-market strategy
4. Build distribution channels
5. Launch and iterate based on feedback
"""

        return {
            "strategy": strategy_plan
        }