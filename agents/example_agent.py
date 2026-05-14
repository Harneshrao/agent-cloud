from sdk.agent import Agent


class ExampleAgent(Agent):

    # Agent identity
    name = "example"
    description = "Example agent used for testing the SDK"
    version = "1.0"

    # Router capabilities
    capabilities = [
        "example",
        "demo",
        "test"
    ]

    # Allowed tools
    tools = ["web_search"]

    def run(self, state):

        task = state.get("task")

        print("🧪 Example Agent running")

        result = self.use_tool("web_search", task)

        return {
            "example": result
        }