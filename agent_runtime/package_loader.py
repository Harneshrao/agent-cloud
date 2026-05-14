"""
Load agent package: resolve code_location from DB, extract zip to temp dir, return path.
Workers use this to run deployed agents without loading from repo at startup.
"""

from __future__ import annotations

import tempfile
import uuid
import zipfile
from pathlib import Path
from typing import Optional, Tuple

from database.developer_economy import get_version, get_latest_version
from agent_runtime.storage_paths import resolve_code_location


def load_agent_package(
    agent_id: int,
    version: Optional[str] = None,
    task_id: Optional[int] = None,
) -> Tuple[Path, Path]:
    """
    Load agent package for execution.
    1. Read agent_versions (by version if given, else latest).
    2. Get code_location and resolve to filesystem path.
    3. Extract zip to temp directory (e.g. /tmp/agent_runtime/{task_id or uuid}/).
    4. Return (package_root, extract_root) where package_root contains agent.yaml and agent.py;
       extract_root is the temp dir to remove after execution.
    """
    if version:
        ver = get_version(agent_id, version)
    else:
        ver = get_latest_version(agent_id)
    if not ver or not (ver.get("code_location") or "").strip():
        raise FileNotFoundError(f"No package found for agent_id={agent_id} version={version or 'latest'}")
    code_location = (ver.get("code_location") or "").strip()
    zip_path = resolve_code_location(code_location)
    if not zip_path.is_file():
        raise FileNotFoundError(f"Package file not found: {zip_path}")
    prefix = f"agent_runtime_{task_id}" if task_id else "agent_runtime"
    extract_root = Path(tempfile.gettempdir()) / prefix / str(uuid.uuid4())
    extract_root.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_root)
    except Exception as e:
        import shutil
        shutil.rmtree(extract_root, ignore_errors=True)
        raise RuntimeError(f"Failed to extract package: {e}") from e
    # If zip had a single top-level dir (e.g. competitor_monitor/agent.yaml), use it as root
    root = _package_root(extract_root)
    if root is None:
        import shutil
        shutil.rmtree(extract_root, ignore_errors=True)
        raise ValueError("Extracted package has no agent.yaml at root or in a single top-level folder")
    return (root, extract_root)


def _package_root(extract_dir: Path) -> Optional[Path]:
    """Return directory that contains agent.yaml: extract_dir or its single subdir that has it."""
    if (extract_dir / "agent.yaml").is_file():
        return extract_dir
    subdirs = [d for d in extract_dir.iterdir() if d.is_dir()]
    if len(subdirs) == 1 and (subdirs[0] / "agent.yaml").is_file():
        return subdirs[0]
    for d in subdirs:
        if (d / "agent.yaml").is_file():
            return d
    return None
