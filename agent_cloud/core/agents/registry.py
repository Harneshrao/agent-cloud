"""In-memory agent registry — production wiring injects loaders via `infra` or `app` bootstrap."""

from __future__ import annotations

from typing import Any


_registry: dict[str, Any] = {}


def register(name: str, agent: Any) -> None:
    _registry[name] = agent


def resolve(name: str) -> Any | None:
    return _registry.get(name)
