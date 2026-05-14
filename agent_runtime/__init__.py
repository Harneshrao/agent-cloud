"""
Agent runtime layer for Agent Cloud.

This package is responsible for:
- Discovering filesystem agents under the top-level `agents/` directory
- Providing a small execution engine that runs agents with context
- Offering simple memory/logging abstractions used by the worker
"""

"""
Agent Deployment Runtime: load and execute uploaded agent packages.

- package_loader: load_agent_package(agent_id, version, task_id=None) -> (package_root, extract_root)
- executor: run_deployed_agent(package_root, state, ...) with timeout/memory limits
"""

from agent_runtime.package_loader import load_agent_package
from agent_runtime.executor import run_deployed_agent, install_dependencies

__all__ = ["load_agent_package", "run_deployed_agent", "install_dependencies"]
