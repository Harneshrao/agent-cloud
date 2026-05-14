from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional


@dataclass
class AgentContext:
    """
    Lightweight context passed into every agent run.
    This is intentionally minimal so it can be implemented both in-process
    (local dev) and on the production platform.
    """

    run_id: Optional[int]
    task_id: int
    agent_name: str
    logger: Any
    memory: Any
    tools: Any
    config: Mapping[str, Any]


class AgentBase:
    """
    Base class for Agent Cloud agents.

    Agents are simple Python classes that define metadata and implement an
    async run(inputs, ctx) method.
    """

    name: str = ""
    description: str = ""
    version: str = "0.1.0"
    inputs: Dict[str, type] = {}
    tools: list[str] = []
    capabilities: list[str] = []
    tags: list[str] = []

    async def run(self, inputs: Dict[str, Any], ctx: AgentContext) -> Any:  # pragma: no cover - interface
        raise NotImplementedError

