"""
Validate agent.yaml manifest inside a zip artifact.
"""

from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path
from typing import Any, List, Tuple

from agent_runtime.package_loader import _package_root
from agent_runtime.package_validation import validate_agent_zip
from sdk.package_spec import load_spec

ALLOWED_RUNTIMES = frozenset({"python"})


def validate_manifest_from_zip(zip_path: Path) -> Tuple[bool, dict[str, Any], List[str]]:
    """
    Validate zip structure + agent.yaml. Returns (ok, manifest_dict, errors).
    """
    ok, errors = validate_agent_zip(zip_path)
    if not ok:
        return False, {}, errors

    manifest: dict[str, Any] = {}
    try:
        from agent_runtime.safe_extract import safe_extract_zip

        with zipfile.ZipFile(zip_path, "r") as zf:
            with tempfile.TemporaryDirectory(prefix="agent_manifest_") as tmp:
                safe_extract_zip(zf, Path(tmp))
                root = _package_root(Path(tmp))
                if root is None:
                    return False, {}, ["Could not locate agent.yaml in package"]
                manifest = load_spec(root)
    except Exception as e:
        return False, {}, [str(e)]

    runtime = (manifest.get("runtime") or "python").strip().lower()
    if runtime not in ALLOWED_RUNTIMES:
        errors.append(f"Unsupported runtime '{runtime}'; only python is supported")
    if not manifest.get("version"):
        errors.append("agent.yaml must define 'version'")
    return len(errors) == 0, manifest, errors
