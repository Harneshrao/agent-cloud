from database import agent_pricing as agent_pricing_db


class AgentRegistry:

    def __init__(self):
        self.agents = {}

    def register_agent(self, agent):

        name = getattr(agent, "name", None)

        if not name:
            raise ValueError("Agent must define a name")

        # Make registration idempotent: avoid re-registering agents with the same name.
        if name in self.agents:
            print(f"[Registry] Agent already registered: {name}")
            return

        self.agents[name] = agent

        # Monetization: store price_per_run in agent_pricing when defined
        price_per_run = getattr(agent, "price_per_run", None)
        if price_per_run is not None:
            try:
                currency = getattr(agent, "currency", "USD")
                agent_pricing_db.upsert_agent_pricing(name, float(price_per_run), currency)
            except Exception as e:
                print(f"[Registry] Failed to store agent pricing for {name}: {e}")

        print(f"[Registry] Registered agent: {name}")

    def get_agent(self, name):
        return self.agents.get(name)

    def list_agents(self):
        return list(self.agents.keys())


# Global registry instance
agent_registry = AgentRegistry()