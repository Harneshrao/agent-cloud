"""
Uvicorn entry — re-exports the full Agent Cloud FastAPI app (`api.main`).

Usage:
  uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --workers 4
"""

from __future__ import annotations

from api.main import app

__all__ = ["app"]
