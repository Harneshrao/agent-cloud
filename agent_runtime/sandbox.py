from __future__ import annotations

from pathlib import Path


def get_agent_data_root() -> Path:
    """
    Return the root directory where agents may store data.

    This is a soft sandbox: agents should only read/write within this tree.
    """
    root = Path("data") / "agents"
    root.mkdir(parents=True, exist_ok=True)
    return root


def get_agent_project_path(agent_name: str, project_id: int | None) -> Path:
    """
    Compute a per-agent, per-project path for data storage.
    """
    base = get_agent_data_root() / agent_name
    if project_id is None:
        base = base / "global"
    else:
        base = base / f"project-{project_id}"
    base.mkdir(parents=True, exist_ok=True)
    return base

