"""Plan limits unit tests."""

from __future__ import annotations

import unittest

from services.plan_limits import _EXTRA_LIMITS


class TestPlanLimits(unittest.TestCase):
    def test_free_tier_exists(self) -> None:
        self.assertIn("Free", _EXTRA_LIMITS)
        self.assertGreater(_EXTRA_LIMITS["Free"]["max_concurrent_running"], 0)

    def test_starter_higher_than_free(self) -> None:
        self.assertGreater(
            _EXTRA_LIMITS["Starter"]["max_deployments"],
            _EXTRA_LIMITS["Free"]["max_deployments"],
        )


if __name__ == "__main__":
    unittest.main()
