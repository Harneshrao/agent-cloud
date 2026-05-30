"""Observability helpers (no DB required for event type list)."""

from __future__ import annotations

import unittest

from agent_cloud.infra.observability.operational_context import snapshot


class TestOperationalContext(unittest.TestCase):
    def test_snapshot_keys(self) -> None:
        s = snapshot()
        self.assertIn("trace_id", s)
        self.assertIn("execution_id", s)


if __name__ == "__main__":
    unittest.main()
