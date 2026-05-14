"""Sandbox policy (resource limits, forbidden builtins) — pure data."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SandboxLimits:
    cpu_seconds: float = 60.0
    memory_mb: int = 512
