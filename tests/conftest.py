"""Pytest: ensure DATABASE_URL exists before config.settings is imported by tests."""

from __future__ import annotations

import os

# Allow CI to override; local tests default to same Compose URL as .env.example
os.environ.setdefault(
    "DATABASE_URL",
    os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql://agent:agent@127.0.0.1:5433/agent_cloud",
    ),
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
