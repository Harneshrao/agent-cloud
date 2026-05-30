"""OpenAPI operationId uniqueness (regression for duplicate /system/health)."""

from __future__ import annotations

import os
import unittest


class TestOpenAPIOperationIds(unittest.TestCase):
    def setUp(self) -> None:
        os.environ.setdefault("SKIP_MIGRATION_CHECK", "1")
        os.environ.setdefault("DATABASE_URL", "postgresql://t:t@127.0.0.1:9/x")
        os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:9/0")

    def test_operation_ids_unique(self) -> None:
        from api.main import app

        spec = app.openapi()
        seen: dict[str, str] = {}
        dups: list[str] = []
        for path, methods in (spec.get("paths") or {}).items():
            for method, op in methods.items():
                if method not in ("get", "post", "put", "patch", "delete"):
                    continue
                oid = (op or {}).get("operationId")
                if not oid:
                    continue
                if oid in seen:
                    dups.append(f"{oid}: {seen[oid]} and {method.upper()} {path}")
                else:
                    seen[oid] = f"{method.upper()} {path}"
        self.assertEqual(dups, [], msg="; ".join(dups))


if __name__ == "__main__":
    unittest.main()
