"""
Project-scoped artifact storage (local filesystem).

Layout: {AGENT_STORAGE_ROOT}/projects/{project_id}/artifacts/{artifact_id}/package.zip
"""

from __future__ import annotations

import hashlib
import os
import uuid
from pathlib import Path

from agent_runtime.storage_paths import get_storage_root


def artifact_zip_path(project_id: uuid.UUID, artifact_id: uuid.UUID) -> Path:
    root = get_storage_root() / "projects" / str(project_id) / "artifacts" / str(artifact_id)
    root.mkdir(parents=True, exist_ok=True)
    return root / "package.zip"


def storage_path_relative(project_id: uuid.UUID, artifact_id: uuid.UUID) -> str:
    return f"storage/projects/{project_id}/artifacts/{artifact_id}/package.zip"


def resolve_artifact_path(storage_path: str) -> Path:
    from agent_runtime.storage_paths import _project_root

    root = _project_root().resolve()
    p = Path(storage_path)
    if p.is_absolute():
        resolved = p.resolve()
    else:
        resolved = (root / storage_path).resolve()
    storage_root = get_storage_root().resolve()
    try:
        resolved.relative_to(storage_root)
    except ValueError:
        raise ValueError(f"Artifact path outside storage root: {storage_path}")
    return resolved


def save_artifact_bytes(
    project_id: uuid.UUID, artifact_id: uuid.UUID, data: bytes
) -> tuple[Path, str]:
    """Write zip bytes; return (absolute path, sha256 hex)."""
    max_bytes = int(os.environ.get("MAX_ARTIFACT_BYTES", str(10 * 1024 * 1024)))
    if len(data) > max_bytes:
        raise ValueError(f"Artifact exceeds max size ({max_bytes} bytes)")
    dest = artifact_zip_path(project_id, artifact_id)
    dest.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    return dest, digest


def verify_checksum(path: Path, expected_sha256: str) -> bool:
    if not path.is_file():
        return False
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest.lower() == (expected_sha256 or "").lower()
