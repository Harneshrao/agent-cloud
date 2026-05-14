"""Token-bucket math (pure). Redis I/O stays in `infra.redis`."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    allowed: bool
    retry_after_sec: float = 0.0


def sliding_window_allow(
    current_count: int, limit: int, *_unused: object
) -> RateLimitDecision:
    if current_count >= limit:
        return RateLimitDecision(allowed=False, retry_after_sec=60.0)
    return RateLimitDecision(allowed=True)
