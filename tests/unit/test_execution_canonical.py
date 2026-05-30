"""Unit tests for canonical execution helpers (no Redis/Postgres)."""

from __future__ import annotations

import unittest

from execution.backoff import retry_delay_seconds
from workers.dequeue_filters import task_matches_worker


class TestDequeueFilters(unittest.TestCase):
    def test_no_filters_accepts_plain_task(self) -> None:
        self.assertTrue(task_matches_worker({"task": "hello", "agent": "demo"}))

    def test_capability_mismatch(self) -> None:
        parsed = {"required_capabilities": ["gpu"]}
        self.assertFalse(
            task_matches_worker(parsed, worker_capabilities=["python"])
        )
        self.assertTrue(
            task_matches_worker(parsed, worker_capabilities=["gpu", "python"])
        )


class TestBackoff(unittest.TestCase):
    def test_delay_grows_with_retries(self) -> None:
        d0 = retry_delay_seconds(0, jitter_max_sec=0)
        d2 = retry_delay_seconds(2, jitter_max_sec=0)
        self.assertGreater(d2, d0)


if __name__ == "__main__":
    unittest.main()
