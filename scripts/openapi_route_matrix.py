#!/usr/bin/env python3
"""
Build a route matrix from the legacy FastAPI app (OpenAPI + dependency names).

Requires DATABASE_URL in env (engine is created on import; no DB connection until used).
Set SKIP_MIGRATION_CHECK=1 for offline generation.

Usage:
  set SKIP_MIGRATION_CHECK=1
  set DATABASE_URL=postgresql://user:pass@localhost:5432/agent_cloud
  python scripts/openapi_route_matrix.py
  python scripts/openapi_route_matrix.py --out docs/generated/route_matrix.md

Optional second app (modular migration target):
  python scripts/openapi_route_matrix.py --app agent_cloud.app.api.main:app
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from pathlib import Path


def _load_app(symbol: str):
    if ":" not in symbol:
        raise SystemExit("APP must be like 'api.main:app'")
    mod_name, attr = symbol.split(":", 1)
    mod = importlib.import_module(mod_name)
    app = getattr(mod, attr)
    return app


def _collect_dependency_names(dep, seen: set[int] | None = None) -> list[str]:
    if dep is None:
        return []
    if seen is None:
        seen = set()
    if id(dep) in seen:
        return []
    seen.add(id(dep))
    out: list[str] = []
    call = getattr(dep, "call", None)
    if call is not None:
        out.append(getattr(call, "__name__", repr(call)))
    for sub in getattr(dep, "dependencies", []) or []:
        out.extend(_collect_dependency_names(sub, seen))
    return out


def flatten_routes(app) -> list[dict]:
    rows: list[dict] = []
    for route in app.routes:
        methods = getattr(route, "methods", None) or {"GET"}
        path = getattr(route, "path", None)
        if path is None:
            continue
        name = getattr(route, "name", "")
        tags = ",".join(getattr(route, "tags", []) or [])
        deps: list[str] = []
        d = getattr(route, "dependant", None)
        if d is not None:
            deps = _collect_dependency_names(d)
        for method in sorted(m for m in methods if m != "HEAD"):
            rows.append(
                {
                    "method": method,
                    "path": path,
                    "name": name,
                    "tags": tags,
                    "deps": ";".join(dict.fromkeys(deps)) if deps else "",
                }
            )
    rows.sort(key=lambda r: (r["path"], r["method"]))
    return rows


def to_markdown(rows: list[dict], title: str) -> str:
    lines = [
        f"# {title}",
        "",
        "| Method | Path | Endpoint name | Tags | Dependency hints |",
        "|--------|------|-----------------|------|------------------|",
    ]
    for r in rows:
        deps = r["deps"].replace("|", "\\|")
        lines.append(
            f"| {r['method']} | `{r['path']}` | {r['name']} | {r['tags']} | {deps} |"
        )
    lines.append("")
    lines.append(f"_Total routes: {len(rows)}_")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--app",
        default="api.main:app",
        help="Module:attribute for FastAPI app (default: api.main:app)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Write Markdown matrix to this path",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Add to sys.path (default: repo root)",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Also write machine-readable bundle: OpenAPI spec + flattened routes",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    sys.path.insert(0, str(root))
    os.chdir(root)

    os.environ.setdefault("SKIP_MIGRATION_CHECK", "1")
    if not os.environ.get("DATABASE_URL", "").strip():
        os.environ["DATABASE_URL"] = (
            "postgresql://inventory:inventory@127.0.0.1:65432/agent_cloud_inventory"
        )
    os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6379/0")

    app = _load_app(args.app)
    rows = flatten_routes(app)
    md = to_markdown(rows, f"Route matrix: `{args.app}`")

    if args.json_out:
        bundle = {
            "format": "agent-cloud.openapi_route_bundle.v1",
            "app": args.app,
            "routes": rows,
            "openapi": app.openapi(),
        }
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
        print(f"Wrote {args.json_out} (openapi + {len(rows)} routes)")

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(md, encoding="utf-8")
        print(f"Wrote {args.out} ({len(rows)} rows)")
    else:
        print(md)


if __name__ == "__main__":
    main()
