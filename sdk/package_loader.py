"""
Agent package loader: read agent.yaml, load entrypoint module, register agent.

Supports loading agents from external packages (agent.yaml + agent.py).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from sdk.agent import Agent
from sdk.package_spec import load_spec
from registry.agent_registry import agent_registry


def _load_module_from_file(module_name: str, file_path: Path) -> Any:
    """Load a Python module from a file path. Returns the module object."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {file_path}")
    module = importlib.util.module_from_spec(spec)
    if module_name in sys.modules:
        return sys.modules[module_name]
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _find_agent_class(module: Any) -> Optional[type]:
    """Return the first Agent subclass defined in the module (excluding Agent itself)."""
    for attr_name in dir(module):
        obj = getattr(module, attr_name)
        if (
            isinstance(obj, type)
            and issubclass(obj, Agent)
            and obj is not Agent
        ):
            return obj
    return None


def load_package(package_dir: str | Path) -> Dict[str, Any]:
    """
    Load an agent package from a directory.

    1. Read agent.yaml (via package_spec.load_spec).
    2. Load the entrypoint module (e.g. agent.py).
    3. Find the Agent subclass and register it in agent_registry.

    Returns the package spec dict. Raises on missing/invalid spec or no Agent class.
    """
    package_dir = Path(package_dir).resolve()
    if not package_dir.is_dir():
        raise FileNotFoundError(f"Package directory not found: {package_dir}")

    spec = load_spec(package_dir)
    entrypoint = spec.get("entrypoint") or "agent.py"
    entry_path = package_dir / entrypoint
    if not entry_path.is_file():
        raise FileNotFoundError(f"Entrypoint not found: {package_dir / entrypoint}")

    # Use a unique module name to avoid clashes when loading multiple packages.
    package_name = spec.get("name", "agent").replace(".", "_").replace("-", "_")
    module_name = f"agent_pkg_{package_name}_{id(package_dir)}"
    module = _load_module_from_file(module_name, entry_path)

    agent_cls = _find_agent_class(module)
    if agent_cls is None:
        raise ValueError(f"No Agent subclass found in {entry_path}")

    # Ensure agent instance has name from spec (override if different).
    agent = agent_cls()
    if hasattr(agent, "name") and spec.get("name"):
        agent.name = spec["name"]
    if spec.get("description") and not getattr(agent, "description", ""):
        agent.description = spec["description"]
    if spec.get("version") and not getattr(agent, "version", ""):
        agent.version = spec["version"]
    if spec.get("capabilities") and not getattr(agent, "capabilities", None):
        agent.capabilities = spec["capabilities"]

    agent_registry.register_agent(agent)
    return spec


def load_packages_from_dirs(package_dirs: List[str | Path]) -> List[Dict[str, Any]]:
    """
    Load all agent packages from the given list of directories.
    Skips packages that fail to load (optional: log and continue).
    Returns list of successfully loaded specs.
    """
    loaded = []
    for d in package_dirs:
        try:
            spec = load_package(d)
            loaded.append(spec)
        except Exception:
            continue
    return loaded
