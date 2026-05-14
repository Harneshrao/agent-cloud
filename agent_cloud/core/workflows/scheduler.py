"""Workflow scheduling decisions (pure)."""

from __future__ import annotations

from uuid import UUID


def should_enqueue_node(
    node_id: str, completed: set[str], deps: list[str]
) -> bool:
    return all(d in completed for d in deps) and node_id not in completed
