from sdk.agent import Agent


class ContentAgent(Agent):

    name = "content"
    description = "Generates articles, reports, or written content based on strategy"
    version = "1.1"

    # Capabilities used by capability routing
    capabilities = [
        "content",
        "writing",
        "article",
        "blog",
        "report",
        "documentation"
    ]

    tools = []

    def run(self, state):

        strategy = state.get("strategy")
        research = state.get("research")

        print("✍ Content Agent generating content")

        content_output = f"""
Content Draft

Title: The Future of AI Agent Platforms

Research Background:
{research}

Strategy Summary:
{strategy}

Article

Artificial Intelligence agents are becoming the foundation
for next-generation software platforms. Businesses are now
leveraging autonomous systems to perform research,
planning, execution, and analysis.

The opportunity in AI automation continues to grow as
companies search for scalable ways to improve productivity
and reduce operational costs.
"""

        return {
            "content": content_output
        }