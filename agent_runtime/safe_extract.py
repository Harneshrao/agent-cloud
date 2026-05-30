"""
Safe ZIP extraction — defense-in-depth against zip-slip and path traversal.

Use instead of ZipFile.extractall() everywhere untrusted archives are unpacked.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from agent_runtime.package_validation import _is_safe_member


class UnsafeArchiveError(ValueError):
    """Raised when a zip member fails safety checks or would escape dest."""


def safe_extract_zip(zf: zipfile.ZipFile, dest_dir: Path) -> None:
    """
    Extract zip members into dest_dir with per-member path validation.
    Rejects unsafe names and paths that resolve outside dest_dir.
    """
    dest = Path(dest_dir).resolve()
    dest.mkdir(parents=True, exist_ok=True)
    for info in zf.infolist():
        if info.is_dir():
            continue
        name = info.filename.replace("\\", "/").rstrip("/")
        if not name or not _is_safe_member(name):
            raise UnsafeArchiveError(f"Unsafe path in archive: {info.filename}")
        target = (dest / name).resolve()
        try:
            target.relative_to(dest)
        except ValueError:
            raise UnsafeArchiveError(
                f"Extract path escapes destination: {info.filename}"
            ) from None
        target.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(info) as src, open(target, "wb") as out:
            while True:
                chunk = src.read(65536)
                if not chunk:
                    break
                out.write(chunk)
