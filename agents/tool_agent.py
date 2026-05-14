from sdk.agent import Agent


class ToolAgent(Agent):
    """Prepares structured tool-call context from prior pipeline outputs (research, strategy)."""

    name = "tool"
    description = "Summarizes tool/API steps implied by research and strategy for downstream execution"
    version = "1.0"
    capabilities = ["tools", "tooling", "api", "integration"]

    tools = []

    def run(self, state):
        research = state.get("research")
        strategy = state.get("strategy")
        task = state.get("task", "")

        print("🔧 Tool Agent assembling tool context")

        lines = [
            "Tool plan (suggested integrations)",
            "",
            f"Task: {task[:500] if task else '(none)'}",
            "",
            "From research:",
            str(research)[:2000] if research is not None else "(none)",
            "",
            "From strategy:",
            str(strategy)[:2000] if strategy is not None else "(none)",
            "",
            "Recommended actions: validate APIs, apply rate limits, log calls for billing.",
        ]
        tool_summary = "\n".join(lines)

        return {"tool": tool_summary}
