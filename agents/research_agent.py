from sdk.agent import Agent
from memory.memory_engine import store_memory, search_memory
from memory.memory_store import memory_store


class ResearchAgent(Agent):

    name = "research"
    description = "Performs topic and market research"
    version = "1.1"

    # Capabilities used by capability router
    capabilities = [
        "research",
        "analysis",
        "market",
        "study",
        "investigate",
        "explore",
        "trend"
    ]

    # Tools available to this agent
    tools = ["web_search"]

    def run(self, state):

        task = state.get("task")

        print("🔎 Research Agent analyzing:", task)

        # --------------------------------
        # Retrieve previous knowledge
        # --------------------------------
        previous_memories = memory_store.retrieve_memory(task)

        if previous_memories:
            print(f"\nPrevious knowledge found: {len(previous_memories)}")
        else:
            print("\nPrevious knowledge: None")

        # --------------------------------
        # Semantic memory search
        # --------------------------------
        memory_results = search_memory(task)

        context = ""

        if memory_results and len(memory_results[0]) > 0:
            context = "\nPrevious insight:\n" + memory_results[0][0]

        # --------------------------------
        # Generate research insights
        # --------------------------------
        insights = """
- Market demand increasing
- Competitors fragmented
- Strong opportunity for AI automation
"""

        result = f"""
Research Report
Topic: {task}

{context}

Market Insights:
{insights}
"""

        # --------------------------------
        # Store insights only (not full report)
        # --------------------------------
        clean_insights = insights.strip()

        store_memory(clean_insights)
        memory_store.store_memory(task, clean_insights)

        # --------------------------------
        # Return standardized output
        # --------------------------------
        return {
            "research": result,
            "insights": clean_insights
        }