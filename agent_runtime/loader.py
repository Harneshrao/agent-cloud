from __future__ import annotations

import importlib
from pathlib import Path
from typing import Dict, Optional, Type

from agentcloud_sdk.agent import AgentBase


_AGENT_CLASSES: Dict[str, Type[AgentBase]] = {}


def _default_agents_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "agents"


def discover_agents(base_dir: Optional[Path] = None) -> None:
    """
    Discover filesystem-based agents under agents/*/agent.py.

    Agents must define at least one subclass of AgentBase. The class-level
    `name` attribute is used as the registry key; if missing, the folder
    name is used.
    """
    base = base_dir or _default_agents_dir()
    if not base.exists():
        return

    for pkg in base.iterdir():
        if not pkg.is_dir():
            continue
        module_name = f"agents.{pkg.name}.agent"
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            continue

        # Prefer classes exported in __all__, fall back to scanning attributes.
        attr_names = getattr(module, "__all__", None) or dir(module)
        for attr_name in attr_names:
            obj = getattr(module, attr_name, None)
            if (
                isinstance(obj, type)
                and issubclass(obj, AgentBase)
                and obj is not AgentBase
            ):
                agent_cls: Type[AgentBase] = obj
                agent_name = getattr(agent_cls, "name", pkg.name) or pkg.name
                _AGENT_CLASSES[agent_name] = agent_cls


def get_agent_class(name: str) -> Optional[Type[AgentBase]]:
    """Return the AgentBase subclass for the given agent name, if any."""
    return _AGENT_CLASSES.get(name)


def list_agents() -> Dict[str, Type[AgentBase]]:
    """Return a copy of the registered agent classes."""
    return dict(_AGENT_CLASSES)

