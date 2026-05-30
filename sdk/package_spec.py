"""
Agent package spec: schema and parsing for agent.yaml.

Expected structure:
  name: str
  version: str
  description: str
  capabilities: list[str]
  entrypoint: str  (e.g. agent.py)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore


def load_spec(package_dir: str | Path) -> Dict[str, Any]:
    """
    Load and parse agent.yaml from a package directory.
    Returns a dict with name, version, description, capabilities, entrypoint.
    Raises FileNotFoundError if agent.yaml is missing, ValueError if invalid.
    """
    path = Path(package_dir) / "agent.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"agent.yaml not found in {package_dir}")

    raw = path.read_text(encoding="utf-8", errors="replace")
    if yaml is None:
        raise ImportError("PyYAML is required to load agent packages. Install with: pip install pyyaml")

    data = yaml.safe_load(raw)
    if not isinstance(data, dict):
        raise ValueError("agent.yaml must be a YAML object")
    name = data.get("name")
    if not name or not str(name).strip():
        raise ValueError("agent.yaml must define 'name'")
    spec = {
        "name": str(name).strip(),
        "version": str(data.get("version") or "").strip(),
        "description": str(data.get("description") or "").strip(),
        "capabilities": _ensure_capabilities_list(data.get("capabilities")),
        "entrypoint": str(data.get("entrypoint") or "agent.py").strip(),
        "runtime": str(data.get("runtime") or "python").strip().lower(),
    }
    return spec


def _ensure_capabilities_list(capabilities: Any) -> List[str]:
    """Normalize capabilities to a list of strings."""
    if capabilities is None:
        return []
    if isinstance(capabilities, list):
        return [str(c).strip() for c in capabilities if c]
    if isinstance(capabilities, str):
        return [capabilities.strip()] if capabilities.strip() else []
    return []

