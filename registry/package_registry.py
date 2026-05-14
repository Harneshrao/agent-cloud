"""
In-memory registry of automation packages.

Stores package name, version, description, agents list, workflow definition, filesystem path.
Used by package loader and package installer.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class PackageRegistry:
    """In-memory registry of loaded automation packages."""

    def __init__(self) -> None:
        self._packages: Dict[str, Dict[str, Any]] = {}

    def register_package(self, name: str, metadata: Dict[str, Any]) -> None:
        """Register a package. metadata should include version, description, agents, workflow, path."""
        self._packages[name] = dict(metadata)
        self._packages[name]["name"] = name

    def get_package(self, name: str) -> Optional[Dict[str, Any]]:
        """Return package metadata by name, or None."""
        return self._packages.get(name)

    def list_packages(self) -> List[Dict[str, Any]]:
        """Return all registered packages (list of metadata dicts)."""
        return list(self._packages.values())


# Global registry instance
package_registry = PackageRegistry()
