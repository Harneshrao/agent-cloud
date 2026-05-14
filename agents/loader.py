import importlib
import os
from pathlib import Path

from sdk.agent import Agent
from sdk.package_loader import load_package
from registry.agent_registry import agent_registry


_agents_loaded = False


def load_agents():
    global _agents_loaded

    if _agents_loaded:
        return agent_registry

    agents_path = os.path.dirname(__file__)
    root = Path(agents_path).resolve().parent

    # 1. Load built-in agents (Python files in agents/)
    for file in os.listdir(agents_path):
        if not file.endswith("_agent.py"):
            continue
        module_name = f"agents.{file[:-3]}"
        module = importlib.import_module(module_name)
        for attr in dir(module):
            obj = getattr(module, attr)
            if (
                isinstance(obj, type)
                and issubclass(obj, Agent)
                and obj is not Agent
            ):
                agent = obj()
                agent_registry.register_agent(agent)

    # 2. Load agents from packages (agent.yaml + entrypoint in agent_packages/)
    package_root = root / "agent_packages"
    if package_root.is_dir():
        for item in package_root.iterdir():
            if item.is_dir() and (item / "agent.yaml").is_file():
                try:
                    load_package(item)
                except Exception:
                    pass

    _agents_loaded = True
    return agent_registry