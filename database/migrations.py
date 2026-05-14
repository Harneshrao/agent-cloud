"""
Legacy module: runtime DDL removed. Use `alembic upgrade head` only.

Kept for optional `run_migrations()` no-op imports from older modules.
"""

from __future__ import annotations


def run_migrations() -> None:
    """No-op: identity and auth tables are created by Alembic revisions."""
    return
