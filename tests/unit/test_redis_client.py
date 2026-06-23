"""Redis client URL normalization and repair predicate tests."""

from __future__ import annotations

import sys
import unittest
from unittest import mock

from redis_queue_pkg.redis_client import normalize_redis_url


class TestNormalizeRedisUrl(unittest.TestCase):
    def test_windows_localhost_to_127(self) -> None:
        with mock.patch.object(sys, "platform", "win32"):
            url = normalize_redis_url("redis://localhost:6379/0")
            self.assertIn("127.0.0.1", url)
            self.assertNotIn("localhost", url)

    def test_linux_unchanged(self) -> None:
        with mock.patch.object(sys, "platform", "linux"):
            url = normalize_redis_url("redis://localhost:6379/0")
            self.assertEqual(url, "redis://localhost:6379/0")


if __name__ == "__main__":
    unittest.main()
