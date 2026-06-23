"""Legacy deployment status repair rules."""

from __future__ import annotations

import unittest

from database.deployment_legacy_repair import should_repair_rolled_back_to_superseded


class TestLegacyRepairPredicate(unittest.TestCase):
    def test_promotion_superseded(self) -> None:
        self.assertTrue(
            should_repair_rolled_back_to_superseded(
                has_rollback_event=False,
                prior_version_is_active=False,
                has_newer_active_same_agent=True,
            )
        )

    def test_user_rollback_preserved_by_event(self) -> None:
        self.assertFalse(
            should_repair_rolled_back_to_superseded(
                has_rollback_event=True,
                prior_version_is_active=False,
                has_newer_active_same_agent=True,
            )
        )

    def test_user_rollback_preserved_by_prior_active(self) -> None:
        self.assertFalse(
            should_repair_rolled_back_to_superseded(
                has_rollback_event=False,
                prior_version_is_active=True,
                has_newer_active_same_agent=False,
            )
        )

    def test_no_newer_active_skipped(self) -> None:
        self.assertFalse(
            should_repair_rolled_back_to_superseded(
                has_rollback_event=False,
                prior_version_is_active=False,
                has_newer_active_same_agent=False,
            )
        )


if __name__ == "__main__":
    unittest.main()
