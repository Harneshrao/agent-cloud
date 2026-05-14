"""
Simple circuit breaker for flaky dependencies (executor, external APIs).

States: closed → open (after failure_threshold) → half-open after cooldown.
"""

from __future__ import annotations

import threading
import time
from typing import Callable, Generic, TypeVar

T = TypeVar("T")


class CircuitOpenError(RuntimeError):
    """Raised when the breaker is open and calls are rejected."""


class CircuitBreaker(Generic[T]):
    def __init__(
        self,
        *,
        failure_threshold: int = 5,
        cooldown_sec: float = 30.0,
        name: str = "default",
    ) -> None:
        self._failure_threshold = max(1, failure_threshold)
        self._cooldown_sec = cooldown_sec
        self._name = name
        self._failures = 0
        self._opened_at: float | None = None
        self._lock = threading.Lock()

    def _state(self) -> str:
        if self._opened_at is None:
            return "closed"
        if time.monotonic() - self._opened_at >= self._cooldown_sec:
            return "half_open"
        return "open"

    def call(self, fn: Callable[[], T]) -> T:
        with self._lock:
            st = self._state()
            if st == "open":
                raise CircuitOpenError(f"circuit {self._name} is open")
            if st == "half_open":
                self._opened_at = None
                self._failures = 0

        try:
            out = fn()
        except Exception:
            with self._lock:
                self._failures += 1
                if self._failures >= self._failure_threshold:
                    self._opened_at = time.monotonic()
            raise
        else:
            with self._lock:
                self._failures = 0
                self._opened_at = None
            return out
