"""
Load prompts from automation package prompts/ directories and register with prompt_registry.

Prompts are namespaced the same way as package agents: namespace.prompt_name
Example: market_research.research_prompt, market_research.analysis_prompt
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from registry.prompt_registry import prompt_registry


def load_prompts_for_package(package_path: Path, namespace: str) -> List[str]:
    """
    Scan package_path/prompts/ for files, read content, register with namespaced name.
    Prompt name is the file stem (e.g. research_prompt.txt -> research_prompt).
    Returns list of registered namespaced prompt names.
    """
    package_path = package_path.resolve()
    prompts_dir = package_path / "prompts"
    if not prompts_dir.is_dir():
        return []
    registered: List[str] = []
    for f in sorted(prompts_dir.iterdir()):
        if not f.is_file() or f.name.startswith("."):
            continue
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
            prompt_name = f.stem
            namespaced_name = f"{namespace}.{prompt_name}"
            prompt_registry.register_prompt(namespaced_name, content)
            registered.append(namespaced_name)
        except Exception:
            continue
    return registered
