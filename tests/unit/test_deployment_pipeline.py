"""Deployment pipeline promotion vs rollback status semantics."""

from __future__ import annotations

import unittest
import uuid

from agent_cloud.core.deployments import pipeline


class TestDeploymentPipelineStates(unittest.TestCase):
    def test_deployment_states_include_superseded(self) -> None:
        self.assertIn("superseded", pipeline.DEPLOYMENT_STATES)
        self.assertIn("rolled_back", pipeline.DEPLOYMENT_STATES)


if __name__ == "__main__":
    unittest.main()
