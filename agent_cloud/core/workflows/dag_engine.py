"""DAG parsing and topological helpers — no I/O."""

from __future__ import annotations

from typing import Any


def node_ids_in_order(nodes: list[dict[str, Any]]) -> list[str]:
    """Return node ids in list order (topological sort added when deps enforced)."""
    return [str(n.get("id") or "") for n in nodes if isinstance(n, dict)]
