"""
Container entrypoint: load agent from /agent, run Agent().run(input_data), print JSON result to stdout.
Used inside the agentcloud-runtime Docker image. Input is read from /input.json (or INPUT_JSON env).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def main() -> None:
    input_path = os.environ.get("INPUT_JSON", "/input.json")
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            input_data = json.load(f)
    except FileNotFoundError:
        input_data = {}
    except json.JSONDecodeError:
        print(json.dumps({"error": "Invalid /input.json"}))
        sys.exit(1)

    agent_dir = Path("/agent")
    if not agent_dir.is_dir():
        print(json.dumps({"error": "/agent not mounted"}))
        sys.exit(1)

    sys.path.insert(0, str(agent_dir))
    entrypoint = "agent.py"
    agent_yaml = agent_dir / "agent.yaml"
    if agent_yaml.is_file():
        try:
            import yaml
            with open(agent_yaml, "r", encoding="utf-8") as f:
                spec = yaml.safe_load(f) or {}
            entrypoint = (spec.get("entrypoint") or "agent.py").strip()
        except Exception:
            pass

    entry_path = agent_dir / entrypoint
    if not entry_path.is_file():
        print(json.dumps({"error": f"Entrypoint not found: {entrypoint}"}))
        sys.exit(1)

    import importlib.util
    spec_mod = importlib.util.spec_from_file_location("_agent", entry_path)
    if not spec_mod or not spec_mod.loader:
        print(json.dumps({"error": "Failed to load agent module"}))
        sys.exit(1)
    mod = importlib.util.module_from_spec(spec_mod)
    spec_mod.loader.exec_module(mod)

    AgentClass = None
    for attr_name in dir(mod):
        obj = getattr(mod, attr_name)
        if isinstance(obj, type) and hasattr(obj, "run"):
            if attr_name == "Agent":
                AgentClass = obj
                break
            if AgentClass is None:
                AgentClass = obj
    if AgentClass is None:
        print(json.dumps({"error": "No Agent class with run() in entrypoint"}))
        sys.exit(1)

    try:
        agent = AgentClass()
        result = agent.run(input_data)
        if result is None:
            result = {}
        if hasattr(result, "__next__"):
            result = list(result)[-1] if result else {}
        print(json.dumps(result, default=str))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
