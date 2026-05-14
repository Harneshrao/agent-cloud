from __future__ import annotations

from typing import Any, Dict

from sdk.agent import Agent
from registry.tool_registry import get_tool

from engine.safe_execution import run_with_timeout, AgentTimeoutError

# Maximum tool execution time (seconds)
TOOL_TIMEOUT_SECONDS = 15


def execute_tool(tool_name: str, state: Dict[str, Any]) -> Any:
    """
    Look up a tool by name in the registry and execute it with the current state.
    Enforces TOOL_TIMEOUT_SECONDS; on timeout or other failure returns a safe error string and logs.
    """
    tool_fn = get_tool(tool_name)

    if tool_fn is None:
        return f"Tool '{tool_name}' not found"

    try:
        return run_with_timeout(
            lambda: tool_fn(state),
            timeout_seconds=TOOL_TIMEOUT_SECONDS,
            task_id=state.get("task_id"),
            agent_name=None,
        )
    except AgentTimeoutError:
        from api.security_logger import log_tool_execution_timeout
        log_tool_execution_timeout(tool_name, TOOL_TIMEOUT_SECONDS, state.get("task_id"))
        return f"Tool '{tool_name}' failed: execution timeout ({TOOL_TIMEOUT_SECONDS}s)"
    except Exception as e:
        return f"Tool '{tool_name}' failed: {e}"


def run_agent_tools(agent: Agent, state: Dict[str, Any]) -> None:
    """
    Execute all tools declared on the agent and append each result to
    state["tools"] for execution tracing and billing.

    Each tool run appends: {"tool": tool_name, "result": result}.
    Tools are executed sequentially. Each tool receives the full `state`.
    """
    tool_names = getattr(agent, "tools", []) or []
    if not tool_names:
        return

    tools_list = state.get("tools")
    if not isinstance(tools_list, list):
        state["tools"] = tools_list = []

    for tool_name in tool_names:
        print(f"Running tool: {tool_name}")
        result = execute_tool(tool_name, state)
        tools_list.append({"tool": tool_name, "result": result})
