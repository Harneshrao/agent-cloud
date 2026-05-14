"""Agent runtime contract (pure)."""

from __future__ import annotations

from typing import Any, Protocol


class AgentExecutor(Protocol):
    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        ...
