"""
SQLAlchemy ORM models — single source of truth for DDL (see Alembic).

During migration, canonical models may still live in `database/models.py`.
Consolidate here when cutting over: `from database.models import Base` then re-export.
"""

from __future__ import annotations

# Re-export for new code paths; Alembic `env.py` may continue to use `database.models`.
from database.models import (  # noqa: F401
    Base,
    Task,
    TaskStatus,
    User,
    Project,
)
