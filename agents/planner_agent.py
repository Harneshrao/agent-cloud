"""
Planner agent: analyzes the task and returns a dynamic workflow (list of agent names).
Used by the orchestrator before routing when no specific agent is requested.
"""

from sdk.agent import Agent


class PlannerAgent(Agent):
    name = "planner_agent"
    description = "Analyzes tasks and returns a workflow of agents to run"
    version = "1.0"
    capabilities = ["planning"]

    tools = []

    def run(self, state):
        task = state.get("task", "")
        if not task:
            return {"workflow": ["research", "execution"]}

        # Analyze task and decide workflow. Use registered agent names.
        task_lower = task.lower()
        workflow = []

        if any(
            w in task_lower
            for w in ("research", "market", "analyze", "study", "investigate", "explore")
        ):
            workflow.append("research")
        if any(w in task_lower for w in ("strategy", "plan", "approach")):
            workflow.append("strategy")
        if any(w in task_lower for w in ("content", "write", "draft")):
            workflow.append("content")
        if any(w in task_lower for w in ("execute", "finalize", "complete", "result")):
            pass  # execution added below

        if "execution" not in workflow:
            workflow.append("execution")

        if not workflow:
            workflow = ["research", "execution"]

        return {"workflow": workflow}
