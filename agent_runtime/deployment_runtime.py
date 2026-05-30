"""
Execute tasks against an active deployment (uploaded ZIP artifact).
"""

from __future__ import annotations

import os
import shutil
import uuid
import zipfile
from pathlib import Path
from typing import Any, Dict, Optional

from agent_runtime.deployment_storage import resolve_artifact_path
from agent_runtime.docker_executor import run_agent_in_container, use_docker_runtime
from agent_runtime.executor import run_deployed_agent
from agent_runtime.package_loader import _package_root
from agent_runtime.safe_extract import safe_extract_zip
from database import deployment_store as store
from engine.safe_execution import run_with_timeout
def _execution_timeout_seconds() -> int:
    try:
        return max(5, int(os.environ.get("AGENT_TIMEOUT_SECONDS", "60")))
    except ValueError:
        return 60


def _require_docker_for_deployments() -> bool:
    v = (os.environ.get("REQUIRE_DOCKER_FOR_DEPLOYMENTS") or "").strip().lower()
    return v in ("1", "true", "yes")


def execute_deployment_task(
    task_id: uuid.UUID,
    deployment_id: uuid.UUID,
    inputs: Dict[str, Any],
    *,
    project_id: Optional[uuid.UUID] = None,
) -> Any:
    dep = store.get_deployment(deployment_id)
    if dep is None:
        raise RuntimeError(f"Deployment not found: {deployment_id}")
    if dep["status"] != "active":
        raise RuntimeError(
            f"Deployment {deployment_id} is not active (status={dep['status']})"
        )
    if project_id is not None and dep["project_id"] != str(project_id):
        raise RuntimeError("Deployment does not belong to this project")

    art = store.get_artifact(uuid.UUID(dep["artifact_id"]))
    if art is None or art["status"] != "validated":
        raise RuntimeError("Deployment artifact missing or invalid")

    zip_path = resolve_artifact_path(art["storage_path"])
    if not zip_path.is_file():
        raise FileNotFoundError(f"Artifact package not found: {zip_path}")

    extract_root = zip_path.parent / f"_run_{task_id}"
    extract_root.mkdir(parents=True, exist_ok=True)
    timeout = _execution_timeout_seconds()
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            safe_extract_zip(zf, extract_root)
        package_root = _package_root(extract_root)
        if package_root is None:
            raise ValueError("Invalid package layout in artifact")

        state = dict(inputs or {})
        # Full secrets only inside worker; never log raw configuration
        state.update(dep.get("configuration") or {})
        state["deployment_id"] = str(deployment_id)
        state["agent_name"] = dep["agent_name"]
        state["version"] = dep["version"]

        use_docker = use_docker_runtime()
        if _require_docker_for_deployments() and not use_docker:
            raise RuntimeError(
                "REQUIRE_DOCKER_FOR_DEPLOYMENTS is set but USE_DOCKER_RUNTIME is off"
            )

        if use_docker:
            return run_with_timeout(
                lambda: run_agent_in_container(
                    package_root, state, timeout_seconds=timeout
                ),
                timeout_seconds=timeout + 10,
                task_id=task_id,
                agent_name=dep["agent_name"],
            )

        return run_deployed_agent(
            package_root,
            state,
            task_id=task_id,
            agent_name=dep["agent_name"],
            timeout_seconds=timeout,
        )
    finally:
        shutil.rmtree(extract_root, ignore_errors=True)
