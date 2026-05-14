"""
Deployed agent execution: install dependencies, load agent module, run with timeout/memory guard.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from engine.safe_execution import run_with_timeout, AgentTimeoutError, MemoryLimitExceededError

# Default limits (PART 6)
EXECUTION_TIMEOUT_SECONDS = 60
MEMORY_LIMIT_MB = 512
CPU_LIMIT_CORES = 1.0


def _load_agent_yaml(package_root: Path) -> Dict[str, Any]:
    """Parse agent.yaml from package root. Returns dict with entrypoint, name, etc."""
    yaml_path = package_root / "agent.yaml"
    if not yaml_path.is_file():
        return {"entrypoint": "agent.py"}
    try:
        import yaml
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        data = {}
    return {"entrypoint": (data.get("entrypoint") or "agent.py").strip(), **data}


def install_dependencies(package_root: Path) -> None:
    """If requirements.txt exists, install into cache or package_root/deps. Use install_dependencies_and_return_paths for sys.path."""
    from agent_runtime.dependency_cache import install_dependencies_and_return_paths
    install_dependencies_and_return_paths(package_root)


def run_deployed_agent(
    package_root: Path,
    state: Dict[str, Any],
    task_id: Optional[int] = None,
    agent_name: Optional[str] = None,
    timeout_seconds: int = EXECUTION_TIMEOUT_SECONDS,
) -> Any:
    """
    Load agent from package_root (entrypoint from agent.yaml), install deps, run agent.run(state)
    under timeout. Returns the result of agent.run(state).
    Raises AgentTimeoutError or MemoryLimitExceededError if limits exceeded.
    """
    spec_dict = _load_agent_yaml(package_root)
    entrypoint = spec_dict.get("entrypoint", "agent.py")
    entry_path = package_root / entrypoint
    if not entry_path.is_file():
        raise FileNotFoundError(f"Entrypoint not found: {entry_path}")

    from agent_runtime.dependency_cache import install_dependencies_and_return_paths
    sys_path_insert = install_dependencies_and_return_paths(package_root)

    def _run() -> Any:
        added: list = []
        for p in sys_path_insert:
            if p not in sys.path:
                sys.path.insert(0, p)
                added.append(p)
        try:
            mod_name = f"_deployed_agent_{task_id or id(state)}"
            spec = importlib.util.spec_from_file_location(mod_name, entry_path)
            if not spec or not spec.loader:
                raise RuntimeError("Failed to load agent module")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            AgentClass = None
            fallback = None
            for attr_name in dir(mod):
                obj = getattr(mod, attr_name)
                if not isinstance(obj, type) or not hasattr(obj, "run"):
                    continue
                if attr_name == "Agent":
                    AgentClass = obj
                    break
                if fallback is None:
                    fallback = obj
            if AgentClass is None:
                AgentClass = fallback
            if AgentClass is None:
                raise RuntimeError("No Agent class with run() method found in entrypoint")
            agent = AgentClass()
            return agent.run(state)
        finally:
            for p in added:
                if p in sys.path:
                    sys.path.remove(p)

    return run_with_timeout(
        _run,
        timeout_seconds=timeout_seconds,
        task_id=task_id,
        agent_name=agent_name,
    )
