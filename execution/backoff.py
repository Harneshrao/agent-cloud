"""Exponential backoff with jitter for queue:retry scores (epoch milliseconds)."""

from __future__ import annotations

import random
import time
from typing import Final

DEFAULT_BASE_SEC: Final[float] = 1.0
DEFAULT_MAX_SEC: Final[float] = 3600.0


def retry_delay_seconds(
    retries: int,
    base_sec: float = DEFAULT_BASE_SEC,
    max_sec: float = DEFAULT_MAX_SEC,
    jitter_max_sec: float = 3.0,
) -> float:
    """
    delay = min(max_sec, base * 2**retries) + uniform(0, jitter_max_sec)
    """
    exp = min(max_sec, base_sec * (2**max(0, retries)))
    return exp + random.uniform(0.0, jitter_max_sec)


def retry_deadline_ms(
    retries: int,
    base_sec: float = DEFAULT_BASE_SEC,
    max_sec: float = DEFAULT_MAX_SEC,
    jitter_max_sec: float = 3.0,
) -> int:
    """Unix ms when the task should become runnable again."""
    delay = retry_delay_seconds(retries, base_sec, max_sec, jitter_max_sec)
    return int((time.time() + delay) * 1000)
