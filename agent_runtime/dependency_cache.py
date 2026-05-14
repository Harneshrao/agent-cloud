"""
Dependency cache: reuse pip-installed dependencies across agents by hashing requirements.txt.
Cache path: storage/dependency_cache/{sha256(requirements.txt)}/
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from agent_runtime.storage_paths import get_storage_root


def get_dependency_cache_root() -> Path:
    """Root for dependency cache: storage/dependency_cache/"""
    return get_storage_root() / "dependency_cache"


def _validate_requirements_line(line: str) -> None:
    """
    Reject dangerous requirement lines.
    Disallow editable installs, VCS URLs, local file paths, or parent-directory references.
    """
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return
    lowered = stripped.lower()
    forbidden_substrings = ("-e ", "git+", "file://", "../", "..\\")
    if stripped.startswith("-r "):
        raise ValueError("Nested requirements (-r) are not allowed in agent requirements.txt")
    if any(s in lowered for s in forbidden_substrings):
        raise ValueError(f"Disallowed requirement line: {stripped}")


def _validate_requirements(requirements_path: Path) -> None:
    """Validate all lines in requirements.txt before installation."""
    text = requirements_path.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        _validate_requirements_line(line)


def get_requirements_hash(requirements_path: Path) -> str:
    """SHA256 hash of requirements file content (normalized: strip, consistent line endings)."""
    text = requirements_path.read_text(encoding="utf-8", errors="replace")
    normalized = "\n".join(line.strip() for line in text.strip().splitlines() if line.strip())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def get_cache_dir_for_hash(h: str) -> Path:
    """Cache directory for a given hash: storage/dependency_cache/{hash}/"""
    return get_dependency_cache_root() / h


def ensure_dependencies_cached(requirements_path: Path) -> Optional[Path]:
    """
    If requirements_path exists: ensure a cache dir for its hash exists (install if missing),
    return that cache path. If requirements_path missing, return None.
    """
    if not requirements_path.is_file():
        return None
    _validate_requirements(requirements_path)
    h = get_requirements_hash(requirements_path)
    cache_dir = get_cache_dir_for_hash(h)
    if cache_dir.is_dir() and (cache_dir / ".installed").is_file():
        return cache_dir
    cache_dir.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "-r",
                str(requirements_path),
                "--target",
                str(cache_dir),
                "--quiet",
                "--disable-pip-version-check",
            ],
            check=True,
            timeout=120,
            capture_output=True,
        )
        (cache_dir / ".installed").write_text(h, encoding="utf-8")
    except Exception:
        if cache_dir.is_dir():
            import shutil
            shutil.rmtree(cache_dir, ignore_errors=True)
        raise
    return cache_dir


def install_dependencies_and_return_paths(package_root: Path) -> List[str]:
    """
    Resolve dependencies: use cache when possible (hash of requirements.txt).
    Returns list of paths to add to sys.path: [package_root, deps_path].
    """
    sys_path_entries = [str(package_root)]
    req_file = package_root / "requirements.txt"
    if not req_file.is_file():
        return sys_path_entries
    try:
        cache_dir = ensure_dependencies_cached(req_file)
        if cache_dir is not None:
            sys_path_entries.append(str(cache_dir))
            return sys_path_entries
    except Exception:
        # Validation or cache install failed; fall back to per-package deps dir.
        pass
    # Fallback: install into package_root/deps (still validated)
    _validate_requirements(req_file)
    deps_dir = package_root / "deps"
    deps_dir.mkdir(exist_ok=True)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-r",
            str(req_file),
            "--target",
            str(deps_dir),
            "--quiet",
            "--disable-pip-version-check",
        ],
        check=True,
        timeout=120,
        capture_output=True,
    )
    sys_path_entries.append(str(deps_dir))
    return sys_path_entries
