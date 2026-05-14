"""Database session factory."""

from __future__ import annotations

from database.session import SessionLocal, engine

__all__ = ["SessionLocal", "engine"]
