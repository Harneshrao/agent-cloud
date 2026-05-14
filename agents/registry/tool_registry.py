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
        Register a new tool or overwrite an existing one with the same name.
        """
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


# Global registry instance to be used across the application.
tool_registry = ToolRegistry()

