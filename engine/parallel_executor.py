from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, Iterable


AgentFunction = Callable[[Dict[str, Any]], Any]


def run_parallel_agents(agent_functions: Iterable[AgentFunction], state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute multiple agent functions in parallel using a shared state.

    Each agent function is called with the same `state` dictionary.
    The results are collected into a dictionary keyed by the function's __name__.
    """
    results: Dict[str, Any] = {}

    with ThreadPoolExecutor() as executor:
        future_to_name = {
            executor.submit(agent_fn, state): getattr(agent_fn, "__name__", repr(agent_fn))
            for agent_fn in agent_functions
        }

        for future in as_completed(future_to_name):
            name = future_to_name[future]
            try:
                results[name] = future.result()
            except Exception as exc:  # keep simple and readable
                results[name] = f"Agent {name} failed with error: {exc}"

    return results

