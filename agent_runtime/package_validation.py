"""
Validate agent package zip: must contain agent.yaml and agent.py.
Used by upload API and CLI before accepting a package.
"""

from __future__ import annotations

import os
import zipfile
from pathlib import Path
from typing import List, Tuple


REQUIRED_ENTRIES = ("agent.yaml", "agent.py")

# Safety limits
MAX_ARCHIVE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB on disk
MAX_FILES = 100


def _is_safe_member(name: str) -> bool:
    """Return False for absolute paths or any path containing .. segments."""
    # Normalize separators
    name = name.replace("\\", "/")
    if not name:
        return False
    # Reject absolute paths (/foo or C:/foo)
    if name.startswith("/") or (":" in name.split("/")[0]):
        return False
    # Reject parent directory traversal
    parts = [p for p in name.split("/") if p not in ("", ".")]
    if any(p == ".." for p in parts):
        return False
    return True


def validate_agent_zip(zip_path: str | Path) -> Tuple[bool, List[str]]:
    """
    Validate an uploaded agent package zip.

    Checks:
      - path exists and is a file
      - archive size on disk <= MAX_ARCHIVE_SIZE_BYTES
      - file count <= MAX_FILES
      - no zip-slip/path traversal (no absolute paths or .. segments)
      - contains agent.yaml and agent.py (at root or in any subpath)
    Returns (ok, list of error messages).
    """
    errors: List[str] = []
    path = Path(zip_path)
    if not path.is_file():
        return False, [f"Not a file: {path}"]
    try:
        # On-disk size limit
        try:
            size_bytes = path.stat().st_size
            if size_bytes > MAX_ARCHIVE_SIZE_BYTES:
                errors.append("Archive too large (max 10MB)")
        except OSError:
            pass

        with zipfile.ZipFile(path, "r") as zf:
            infos = [zi for zi in zf.infolist() if not zi.is_dir()]
            if len(infos) > MAX_FILES:
                errors.append(f"Archive has too many files (max {MAX_FILES})")

            names: List[str] = []
            for zi in infos:
                name = zi.filename.replace("\\", "/").rstrip("/")
                if not _is_safe_member(name):
                    errors.append(f"Unsafe path in archive: {zi.filename}")
                else:
                    names.append(name)

            has_yaml = any(n == "agent.yaml" or n.endswith("/agent.yaml") for n in names)
            has_py = any(n == "agent.py" or n.endswith("/agent.py") for n in names)
            if not has_yaml:
                errors.append("Package must contain agent.yaml")
            if not has_py:
                errors.append("Package must contain agent.py")
    except zipfile.BadZipFile:
        return False, ["Invalid or corrupted zip file"]
    except Exception as e:
        return False, [str(e)]
    return len(errors) == 0, errors


def validate_agent_zip_from_bytes(data: bytes) -> Tuple[bool, List[str]]:
    """Validate zip from in-memory bytes. Returns (ok, errors)."""
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=True) as f:
        f.write(data)
        f.flush()
        return validate_agent_zip(f.name)
