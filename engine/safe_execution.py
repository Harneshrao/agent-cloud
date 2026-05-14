"""
Safe execution wrappers for agent and tool runs.

- run_with_timeout: run a sync callable in a thread with a time limit; raise AgentTimeoutError if exceeded.
- run_with_memory_guard: run a callable and catch MemoryError; re-raise as SafeExecutionError so worker can mark task failed.

Workers use these so agents cannot run forever or exhaust memory without the worker recovering.
"""

from __future__ import annotations

import threading
from typing import Any, Callable, TypeVar

from api.security_logger import log_agent_timeout, log_memory_limit_exceeded

# Default agent execution timeout (seconds)
AGENT_TIMEOUT_SECONDS = 60

T = TypeVar("T")


class AgentTimeoutError(Exception):
    """Raised when agent execution exceeds the allowed time."""
    def __init__(self, message: str, task_id: int | None = None, agent_name: str | None = None):
        self.task_id = task_id
        self.agent_name = agent_name
        super().__init__(message)


class MemoryLimitExceededError(Exception):
    """Raised when agent execution triggers MemoryError."""
    def __init__(self, message: str, task_id: int | None = None, agent_name: str | None = None):
        self.task_id = task_id
        self.agent_name = agent_name
        super().__init__(message)


def _run_in_thread(
    fn: Callable[[], T],
    result_holder: list,
    exc_holder: list,
) -> None:
    try:
        out = fn()
        result_holder.append(out)
    except MemoryError as e:
        exc_holder.append(MemoryLimitExceededError(f"Memory limit exceeded: {e}"))
    except Exception as e:
        exc_holder.append(e)


def run_with_timeout(
    fn: Callable[[], T],
    timeout_seconds: int = AGENT_TIMEOUT_SECONDS,
    task_id: int | None = None,
    agent_name: str | None = None,
) -> T:
    """
    Run fn() in a daemon thread and wait up to timeout_seconds.
    Returns the result, or raises AgentTimeoutError / MemoryLimitExceededError / other from fn.
    """
    result_holder: list = []
    exc_holder: list = []
    thread = threading.Thread(
        target=_run_in_thread,
        args=(fn, result_holder, exc_holder),
        daemon=True,
    )
    thread.start()
    thread.join(timeout=timeout_seconds)
    if exc_holder:
        e = exc_holder[0]
        if isinstance(e, MemoryLimitExceededError):
            e.task_id = task_id
            e.agent_name = agent_name
            log_memory_limit_exceeded(task_id, agent_name)
        raise e
    if thread.is_alive():
        log_agent_timeout(task_id, agent_name, timeout_seconds)
        raise AgentTimeoutError(
            f"Agent execution exceeded {timeout_seconds}s",
            task_id=task_id,
            agent_name=agent_name,
        )
    if not result_holder:
        raise AgentTimeoutError(
            "Agent did not return a result",
            task_id=task_id,
            agent_name=agent_name,
        )
    return result_holder[0]


def run_with_memory_guard(
    fn: Callable[[], T],
    task_id: int | None = None,
    agent_name: str | None = None,
) -> T:
    """
    Run fn(); on MemoryError log and raise MemoryLimitExceededError so the worker can mark task failed.
    """
    try:
        return fn()
    except MemoryError as e:
        log_memory_limit_exceeded(task_id, agent_name)
        raise MemoryLimitExceededError(f"Memory limit exceeded: {e}", task_id=task_id, agent_name=agent_name)
