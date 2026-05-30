"""Manifest validation unit tests."""

from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from agent_runtime.manifest_validation import validate_manifest_from_zip


class TestDeploymentManifest(unittest.TestCase):
    def _make_zip(self, tmp: Path) -> Path:
        zpath = tmp / "pkg.zip"
        with zipfile.ZipFile(zpath, "w") as zf:
            zf.writestr(
                "agent.yaml",
                "name: test_agent\nversion: 1.0.0\nruntime: python\nentrypoint: agent.py\n",
            )
            zf.writestr("agent.py", "class Agent:\n  def run(self, state): return state\n")
        return zpath

    def test_valid_zip(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            zpath = self._make_zip(Path(d))
            ok, manifest, errors = validate_manifest_from_zip(zpath)
            self.assertTrue(ok, errors)
            self.assertEqual(manifest["name"], "test_agent")


if __name__ == "__main__":
    unittest.main()
