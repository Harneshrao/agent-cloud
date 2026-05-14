"""
In-memory registry of prompts. Used by automation package prompt loader and by agents at runtime.

Prompts are stored by namespaced name (e.g. market_research.research_prompt) for fast access.
"""

from __future__ import annotations

from typing import Dict, List, Optional


class PromptRegistry:
    """In-memory registry of prompt name -> content."""

    def __init__(self) -> None:
        self._prompts: Dict[str, str] = {}

    def register_prompt(self, name: str, content: str) -> None:
        """Register a prompt by name. Overwrites if name already exists."""
        self._prompts[name] = content

    def get_prompt(self, name: str) -> Optional[str]:
        """Return prompt content by name, or None if not found."""
        return self._prompts.get(name)

    def get(self, name: str) -> Optional[str]:
        """Alias for get_prompt for agent usage: prompt_registry.get('market_research.research_prompt')."""
        return self.get_prompt(name)

    def list_prompts(self) -> List[str]:
        """Return all registered prompt names."""
        return list(self._prompts.keys())


# Global registry instance
prompt_registry = PromptRegistry()
