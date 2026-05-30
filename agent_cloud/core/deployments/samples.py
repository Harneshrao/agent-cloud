"""Build onboarding sample agent ZIPs from repo agents/."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path
from typing import Any, Dict

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
ALLOWED_SAMPLES = frozenset({"sample_echo", "sample_fail", "sample_slow"})
SAMPLE_FILES = ("agent.yaml", "agent.py")


def read_sample_manifest(sample_name: str) -> Dict[str, Any]:
    """Read agent.yaml for a built-in sample (name + version)."""
    if sample_name not in ALLOWED_SAMPLES:
        raise ValueError(f"Unknown sample: {sample_name}")
    path = REPO_ROOT / "agents" / sample_name / "agent.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"Sample agent not found: {sample_name}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    name = str(data.get("name") or sample_name).strip()
    version = str(data.get("version") or "0.0.1").strip() or "0.0.1"
    return {"name": name, "version": version, "manifest": data}


def build_sample_zip(sample_name: str) -> bytes:
    if sample_name not in ALLOWED_SAMPLES:
        raise ValueError(f"Unknown sample: {sample_name}")
    root = REPO_ROOT / "agents" / sample_name
    if not root.is_dir():
        raise FileNotFoundError(f"Sample agent not found: {sample_name}")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in SAMPLE_FILES:
            path = root / name
            if not path.is_file():
                raise FileNotFoundError(f"Missing {name} in {sample_name}")
            zf.writestr(name, path.read_bytes())
    return buf.getvalue()
