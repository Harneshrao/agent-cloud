"""
Resolve storage paths for agent packages. Shared by API (upload) and workers (load).
Storage layout: storage/agents/{agent_id}/{version}.zip
"""

from __future__ import annotations

import os
from pathlib import Path


def _project_root() -> Path:
    """Project root: parent of the directory containing this file (agent_runtime)."""
    return Path(__file__).resolve().parent.parent


def get_storage_root() -> Path:
    """Root directory for agent packages. Override with AGENT_STORAGE_ROOT env."""
    root = os.environ.get("AGENT_STORAGE_ROOT", "").strip()
    if root:
        return Path(root)
    return _project_root() / "storage"


def get_agent_package_dir(agent_id: int) -> Path:
    """Directory for one agent's versions: storage/agents/{agent_id}/"""
    return get_storage_root() / "agents" / str(agent_id)


def get_agent_package_path(agent_id: int, version: str) -> Path:
    """Full path to stored zip: storage/agents/{agent_id}/{version}.zip"""
    return get_agent_package_dir(agent_id) / f"{version.strip()}.zip"


def code_location_relative(agent_id: int, version: str) -> str:
    """Relative code_location string stored in DB: storage/agents/{agent_id}/{version}.zip"""
    return f"storage/agents/{agent_id}/{version.strip()}.zip"


def resolve_code_location(code_location: str) -> Path:
    """
    Resolve code_location (relative path or absolute) to a full filesystem path.
    If code_location is relative (e.g. storage/agents/1/1.0.0.zip), resolve from project root.
    """
    p = Path(code_location)
    if p.is_absolute():
        return p
    return _project_root() / code_location
