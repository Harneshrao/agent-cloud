"""
Application settings — re-export from legacy `config.settings` until split.

New code should import from `agent_cloud.infra.config.settings` only.
"""

from __future__ import annotations

from config.settings import (  # noqa: F401
    DATABASE_URL,
    DEFAULT_PROJECT_UUID,
    DEFAULT_USER_UUID,
    REDIS_URL,
)
