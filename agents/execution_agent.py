from sdk.agent import Agent


class ExecutionAgent(Agent):
    name = "execution"
    description = "Final step that compiles results"
    version = "1.0"
    capabilities = ["execute", "finalize", "complete"]

    def run(self, state):
        print("Execution Agent executing final step")

        research = state.get("research")
        strategy = state.get("strategy")
        content = state.get("content")
        tool = state.get("tool")

        result_parts = []

        for part in [research, strategy, content, tool]:
            if part is not None:
                result_parts.append(str(part))

        final_output = "\n\n".join(result_parts)

        return {"result": final_output}