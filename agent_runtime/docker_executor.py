"""
Run deployed agent inside an isolated Docker container.
Use when USE_DOCKER_RUNTIME=1 for secure execution. Falls back to in-process if Docker unavailable.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

# Limits (aligned with safe_execution and spec)
CONTAINER_MEMORY_MB = 512
CONTAINER_CPUS = 1.0
RUNTIME_IMAGE = "agentcloud-runtime"


def run_agent_in_container(
    package_root: Path,
    input_data: Dict[str, Any],
    timeout_seconds: int = 60,
) -> Any:
    """
    Run agent in Docker: mount package_root at /agent, pass input_data as /input.json,
    run runner.py in agentcloud-runtime image. Returns parsed JSON result.
    Raises RuntimeError if container fails or times out.
    """
    package_root = Path(package_root).resolve()
    if not package_root.is_dir():
        raise FileNotFoundError(f"Package root not found: {package_root}")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(input_data, f, default=str)
        input_file = f.name
    try:
        cmd = [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            f"--memory={CONTAINER_MEMORY_MB}m",
            f"--cpus={CONTAINER_CPUS}",
            "--pids-limit=100",
            "--read-only",
            "--security-opt=no-new-privileges",
            "-v",
            f"{package_root}:/agent:ro",
            "-v",
            f"{input_file}:/input.json:ro",
            RUNTIME_IMAGE,
            "python",
            "/runner.py",
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        if result.returncode != 0:
            err = result.stderr.strip() or result.stdout.strip() or "Container failed"
            raise RuntimeError(f"Container exited {result.returncode}: {err}")
        out = result.stdout.strip()
        if not out:
            return {}
        try:
            return json.loads(out)
        except json.JSONDecodeError:
            return {"raw": out}
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Container timed out after {timeout_seconds}s")
    finally:
        try:
            os.unlink(input_file)
        except OSError:
            pass


def use_docker_runtime() -> bool:
    """True if USE_DOCKER_RUNTIME env is set to 1/true/yes."""
    v = (os.environ.get("USE_DOCKER_RUNTIME") or "").strip().lower()
    return v in ("1", "true", "yes")
