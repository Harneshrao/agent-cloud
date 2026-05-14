from __future__ import annotations

import importlib
import os
from typing import Optional


_tools_loaded: bool = False


def load_tools(tools_path: Optional[str] = None) -> None:
    """
    Discover and import all tool modules under the tools/ directory.

    Importing a module is expected to cause it to register its tools with the
    global tool registry (see registry.tool_registry and tools implementations).
    """
    global _tools_loaded

    if _tools_loaded:
        return

    base_path = tools_path or os.path.dirname(__file__)

    for file in os.listdir(base_path):
        # Skip private modules and the loader itself
        if not file.endswith(".py"):
            continue
        if file in ("__init__.py", "loader.py"):
            continue

        module_name = f"tools.{file[:-3]}"
        importlib.import_module(module_name)

    _tools_loaded = True

