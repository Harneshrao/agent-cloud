"""API contract smoke tests for Managed Agent Hosting baseline (stdlib unittest)."""

from __future__ import annotations

import os
import unittest

from fastapi.testclient import TestClient


class TestHealthContract(unittest.TestCase):
    def setUp(self) -> None:
        os.environ.setdefault("SKIP_MIGRATION_CHECK", "1")
        os.environ.setdefault("DATABASE_URL", "postgresql://t:t@127.0.0.1:65432/t")
        os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6379/15")
        from api.main import app

        self.client = TestClient(app)

    def test_health_ok(self) -> None:
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json().get("status"), "ok")

    def test_health_deep_includes_components(self) -> None:
        r = self.client.get("/health?deep=1")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIn("components", body)
        self.assertIn(body.get("status"), ("ok", "degraded"))

    def test_openapi_title(self) -> None:
        r = self.client.get("/openapi.json")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIn("openapi", body)
        self.assertEqual(body.get("info", {}).get("title"), "Agent Cloud API")


if __name__ == "__main__":
    unittest.main()
