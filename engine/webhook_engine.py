"""
Webhook engine: validate webhook source and convert to internal events.

1. Validate webhook source (allowed list).
2. Convert webhook payload into internal event (optional source-specific normalization).
3. Call process_event(event_type, payload).
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List

from engine.event_engine import process_event

# Allowed webhook sources; external callers must use one of these.
ALLOWED_SOURCES = frozenset({"github", "slack", "generic", "webhook"})


def validate_source(source: str) -> bool:
    """Return True if source is an allowed webhook source."""
    return source.lower().strip() in ALLOWED_SOURCES


def _normalize_payload(source: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Optionally convert source-specific payload into a flat dict for task_template substitution.
    GitHub/Slack etc. send nested structures; we flatten or pass through as-is.
    """
    if not payload:
        return {}
    source_lower = source.lower()
    if source_lower == "github":
        # Common GitHub webhook fields for template use.
        out = dict(payload)
        if "repository" in payload and isinstance(payload["repository"], dict):
            repo = payload["repository"]
            out["repo"] = repo.get("full_name") or repo.get("name") or ""
            out["repo_name"] = repo.get("name") or ""
        if "sender" in payload and isinstance(payload["sender"], dict):
            out["sender"] = payload["sender"].get("login") or ""
        return out
    if source_lower == "slack":
        return dict(payload)
    return dict(payload)


def process_webhook(
    source: str,
    event_type: str,
    payload: Dict[str, Any],
    *,
    project_id: uuid.UUID,
) -> List[uuid.UUID]:
    """
    Validate source, normalize payload for the source, then process as internal event.
    Returns list of enqueued task IDs. Raises ValueError if source is not allowed.
    project_id is required — webhooks must not enqueue global (NULL project) tasks.
    """
    if not validate_source(source):
        raise ValueError(f"Unknown or disallowed webhook source: {source}")
    normalized = _normalize_payload(source, payload)
    return process_event(event_type, normalized, project_id=project_id, source="webhook")
