"""
Integration: Redis token bucket (requires REDIS_URL and running Redis).

Run: pytest tests/integration/test_token_bucket.py -v
Skip if Redis unavailable.
"""

from __future__ import annotations

import uuid

import pytest

from agent_cloud.infra.redis.token_bucket import allow, rate_user_key
from config.settings import REDIS_URL


@pytest.fixture
def redis_client():
    try:
        import redis as redis_lib
    except ImportError:
        pytest.skip("redis not installed")
    r = redis_lib.from_url(REDIS_URL, decode_responses=True)
    try:
        r.ping()
    except Exception:
        pytest.skip("Redis not reachable")
    yield r
    key = rate_user_key("test-chaos-user")
    try:
        r.delete(key)
    except Exception:
        pass


def test_token_bucket_allows_then_blocks(redis_client) -> None:
    key = rate_user_key(f"test-{uuid.uuid4().hex}")
    cap, refill = 2.0, 100.0
    assert allow(redis_client, key, capacity=cap, refill_per_sec=refill, cost=1.0) is True
    assert allow(redis_client, key, capacity=cap, refill_per_sec=refill, cost=1.0) is True
    assert allow(redis_client, key, capacity=cap, refill_per_sec=refill, cost=1.0) is False
