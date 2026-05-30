"""Safe ZIP extraction tests."""

from __future__ import annotations

import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from agent_runtime.safe_extract import UnsafeArchiveError, safe_extract_zip


class TestSafeExtract(unittest.TestCase):
    def test_rejects_parent_traversal(self) -> None:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("../evil.txt", b"x")
        buf.seek(0)
        with tempfile.TemporaryDirectory() as tmp:
            with zipfile.ZipFile(buf, "r") as zf:
                with self.assertRaises(UnsafeArchiveError):
                    safe_extract_zip(zf, Path(tmp))

    def test_extracts_safe_member(self) -> None:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("agent.yaml", b"name: test\n")
            zf.writestr("agent.py", b"class Agent:\n pass\n")
        buf.seek(0)
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            with zipfile.ZipFile(buf, "r") as zf:
                safe_extract_zip(zf, dest)
            self.assertTrue((dest / "agent.yaml").is_file())


if __name__ == "__main__":
    unittest.main()
