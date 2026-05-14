from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional


ToolFunction = Callable[..., Any]


@dataclass
class ToolMetadata:
    """
    In-memory description of a tool.

    `input_schema` and `output_schema` are expected to be JSON-serializable schema
    descriptions (e.g. dictionaries following JSON Schema or a similar format).
    """

    name: str
    description: str
    function: ToolFunction
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]


class ToolRegistry:
    """
    Simple in-memory registry for tools in the agent platform.

    Tools are stored by name in a dictionary and can be registered at import time
    or dynamically at runtime.
    """

    def __init__(self) -> None:
        self._tools: Dict[str, ToolMetadata] = {}

    def register_tool(
        self,
        name: str,
        description: str,
        function: ToolFunction,
        input_schema: Optional[Dict[str, Any]] = None,
        output_schema: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Register a new tool by name.

        Registration is idempotent: if a tool with the same name is already
        registered, it will not be overwritten.
        """
        if name in self._tools:
            # Avoid duplicate registration; keep the original definition.
            return

        metadata = ToolMetadata(
            name=name,
            description=description,
            function=function,
            input_schema=input_schema or {},
            output_schema=output_schema or {},
        )
        self._tools[name] = metadata

    def get_tool(self, name: str) -> Optional[ToolMetadata]:
        """
        Retrieve tool metadata by name.

        Returns None if the tool is not registered.
        """
        return self._tools.get(name)

    def list_tools(self) -> Dict[str, ToolMetadata]:
        """
        Return a mapping of all registered tools keyed by tool name.
        """
        return dict(self._tools)


    def get_tool_function(self, name: str) -> Optional[ToolFunction]:
        """
        Convenience accessor returning just the underlying function for a tool.
        """
        meta = self.get_tool(name)
        return meta.function if meta is not None else None


# Global registry instance to be used across the application.
tool_registry = ToolRegistry()


def register_tool(name: str, fn: ToolFunction) -> None:
    """
    Simple helper to register a tool by name and function.
    """
    tool_registry.register_tool(name=name, description=name, function=fn)


def get_tool(name: str) -> Optional[ToolFunction]:
    """
    Simple helper to retrieve a tool function by name.
    """
    return tool_registry.get_tool_function(name)
