"""Structured logging setup (wire uvicorn/gunicorn + JSON in production)."""

from __future__ import annotations

import logging

LOG = logging.getLogger("agent_cloud")


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO))
