"""Unit tests for agent_cloud.core.resilience.circuit_breaker."""

from __future__ import annotations

import pytest

from agent_cloud.core.resilience.circuit_breaker import CircuitBreaker, CircuitOpenError


def test_circuit_opens_after_failures() -> None:
    cb: CircuitBreaker[str] = CircuitBreaker(failure_threshold=2, cooldown_sec=60.0, name="t")
    with pytest.raises(RuntimeError):
        cb.call(lambda: (_ for _ in ()).throw(RuntimeError("x")))
    with pytest.raises(RuntimeError):
        cb.call(lambda: (_ for _ in ()).throw(RuntimeError("x")))
    with pytest.raises(CircuitOpenError):
        cb.call(lambda: "ok")


def test_circuit_recovers_after_success() -> None:
    cb: CircuitBreaker[int] = CircuitBreaker(failure_threshold=3, cooldown_sec=0.01, name="t2")
    assert cb.call(lambda: 1) == 1
    assert cb.call(lambda: 2) == 2
