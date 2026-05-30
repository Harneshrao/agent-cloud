#!/usr/bin/env python3
"""
Emit Phase 1–2 migration artifacts under docs/migration/ (graphs + per-file classification).
Excludes .venv, node_modules, __pycache__, .git, .next, dist, build.
"""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "migration"
SKIP_DIR_NAMES = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "node_modules",
        ".next",
        "dist",
        "build",
        ".eggs",
        "agent_cloud.egg-info",
    }
)


def skip_path(p: Path) -> bool:
    parts = set(p.parts)
    if parts & SKIP_DIR_NAMES:
        return True
    if "node_modules" in p.parts:
        return True
    return False


def iter_source_files() -> list[Path]:
    out: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dp = Path(dirpath)
        if skip_path(dp):
            dirnames[:] = []
            continue
        # prune skip dirs
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_NAMES and not d.endswith(".egg-info")]
        for fn in filenames:
            if fn.endswith((".py", ".tsx", ".ts")) and not fn.endswith(".d.ts"):
                fp = dp / fn
                if skip_path(fp):
                    continue
                out.append(fp)
    return sorted(out)


def top_level_module_from_import(name: str) -> str:
    return name.split(".", 1)[0]


def parse_imports(py_path: Path) -> set[str]:
    try:
        tree = ast.parse(py_path.read_text(encoding="utf-8", errors="replace"), filename=str(py_path))
    except SyntaxError:
        return set()
    mods: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mods.add(top_level_module_from_import(alias.name))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                mods.add(top_level_module_from_import(node.module))
    return mods


def classify_path(rel: str) -> str:
    r = rel.replace("\\", "/")
    if r.startswith("archive/"):
        return "TECH_DEBT"
    if r.startswith("solana_agent/") or r.startswith("archive/solana_agent/"):
        return "REMOVE_FROM_WEDGE"
    if r.startswith("agents/competitor_intelligence/"):
        return "REMOVE_FROM_WEDGE"
    if r.startswith("automation_packages/competitor_research/"):
        return "REMOVE_FROM_WEDGE"
    if r.startswith("kubernetes/") and not r.startswith("deploy/kubernetes"):
        return "DUPLICATE"
    if r.startswith("task_queue/"):
        return "DUPLICATE"
    if r.startswith("app/") and "api" in r:
        return "DUPLICATE"
    if r.startswith("execution/") and r.endswith(".py") and "agent_cloud/execution" not in r:
        return "DUPLICATE"
    if r.startswith("api/war_room") or r.startswith("api/demo_api"):
        return "REMOVE_FROM_WEDGE"
    if r.startswith("core/war_room") or r.startswith("core/goal_mapper"):
        return "REMOVE_FROM_WEDGE"
    if r.startswith("dashboard/") and any(
        x in r for x in ("/marketplace/", "/war-room/", "/developer/", "/workflows/", "/automation/")
    ):
        return "REMOVE_FROM_WEDGE"
    if r.startswith("engine/agent_ranking") or r.startswith("engine/template_ranking"):
        return "REMOVE_FROM_WEDGE"
    if r.startswith("agent_cloud/"):
        return "CORE_RUNTIME"
    if r.startswith("workers/") or r.startswith("services/") or r.startswith("redis_queue_pkg/"):
        return "CORE_RUNTIME"
    if r.startswith("database/"):
        if any(
            x in r
            for x in (
                "developer_",
                "agent_store",
                "agent_ratings",
                "agent_pricing",
                "agent_revenue",
                "simulation",
                "knowledge_graph",
                "template_",
                "package_stats",
            )
        ):
            return "REMOVE_FROM_WEDGE"
        return "CORE_RUNTIME"
    if r.startswith("api/"):
        if any(
            x in r
            for x in (
                "war_room",
                "demo_api",
                "developers_economy",
                "marketplace_api",
                "agent_marketplace",
                "simulation",
                "packages_api",
                "template_versions",
                "templates_api",
            )
        ):
            return "REMOVE_FROM_WEDGE"
        return "CORE_RUNTIME"
    if r.startswith("alembic/"):
        return "CORE_RUNTIME"
    if r.startswith("deploy/"):
        return "CORE_RUNTIME"
    if r.startswith("dashboard/"):
        return "CORE_RUNTIME"
    if r.startswith("docs/"):
        return "SUPPORTING"
    if r.startswith("tests/"):
        return "SUPPORTING"
    if r.startswith("scripts/") or r.startswith("tools/"):
        return "SUPPORTING"
    if r.startswith("orchestrator/") or r.startswith("scheduler/") or r.startswith("engine/"):
        return "CORE_RUNTIME"
    if r.startswith("agent_runtime/"):
        return "CORE_RUNTIME"
    if r.startswith("config/"):
        return "CORE_RUNTIME"
    if r.startswith("memory/"):
        return "FUTURE"
    if r.startswith("registry/"):
        return "SUPPORTING"
    if r.startswith("agents/"):
        return "SUPPORTING"
    if r.startswith("automation_packages/"):
        return "FUTURE"
    if r.startswith("contracts/"):
        return "CORE_RUNTIME"
    if r.startswith("gateway/"):
        return "TECH_DEBT"
    return "SUPPORTING"


def folder_edges() -> dict[str, list[str]]:
    """folder -> list of folder names imported by any .py file in that folder (heuristic)."""
    edges: dict[str, set[str]] = defaultdict(set)
    for fp in iter_source_files():
        if fp.suffix != ".py":
            continue
        rel = str(fp.relative_to(ROOT))
        if skip_path(fp):
            continue
        folder = str(fp.relative_to(ROOT).parent).replace("\\", "/") or "."
        imps = parse_imports(fp)
        for m in imps:
            if m in ("api", "database", "workers", "config", "services", "redis_queue_pkg", "agent_cloud", "agent_runtime", "orchestrator", "engine", "fastapi", "pydantic", "sqlalchemy", "redis"):
                edges[folder].add(m)
    return {k: sorted(v) for k, v in sorted(edges.items())}


def openapi_routes() -> dict:
    env = os.environ.copy()
    env.setdefault("SKIP_MIGRATION_CHECK", "1")
    env.setdefault("DATABASE_URL", "postgresql://m:m@127.0.0.1:9/x")
    env.setdefault("REDIS_URL", "redis://127.0.0.1:9/0")
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "openapi_route_matrix.py"),
        "--app",
        "api.main:app",
        "--json-out",
        str(OUT / "_openapi_legacy_tmp.json"),
    ]
    subprocess.run(cmd, cwd=str(ROOT), env=env, check=False, capture_output=True)
    p = OUT / "_openapi_legacy_tmp.json"
    if not p.exists():
        return {"error": "openapi bundle not generated"}
    data = json.loads(p.read_text(encoding="utf-8"))
    routes = data.get("routes", [])
    p.unlink(missing_ok=True)
    return {"app": "api.main:app", "route_count": len(routes), "routes": routes}


def model_graph() -> dict:
    models = ROOT / "database" / "models.py"
    if not models.exists():
        return {}
    tree = ast.parse(models.read_text(encoding="utf-8"), filename=str(models))
    tables: list[dict] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            for sub in node.body:
                if not isinstance(sub, ast.Assign):
                    continue
                for t in sub.targets:
                    if isinstance(t, ast.Name) and t.id == "__tablename__":
                        if isinstance(sub.value, ast.Constant) and isinstance(sub.value.value, str):
                            tables.append({"class": node.name, "table": sub.value.value})
                        break
    return {"models_py": tables}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    files = [str(p.relative_to(ROOT)).replace("\\", "/") for p in iter_source_files()]
    classification = {f: classify_path(f) for f in files}
    bucket_counts: dict[str, int] = defaultdict(int)
    for b in classification.values():
        bucket_counts[b] += 1

    phase1 = {
        "folder_dependency_hints": folder_edges(),
        "openapi": openapi_routes(),
        "database_models": model_graph(),
        "note": "Import graph is first-party top-level hints only; not a full symbol graph.",
    }
    (OUT / "phase1_graphs.json").write_text(json.dumps(phase1, indent=2), encoding="utf-8")
    (OUT / "phase2_classification.json").write_text(
        json.dumps(
            {
                "file_count": len(classification),
                "bucket_counts": dict(bucket_counts),
                "files": classification,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    report = [
        "# Migration intelligence report (auto-generated)",
        "",
        f"- Source files scanned: **{len(files)}** (.py, .ts, .tsx excluding vendor caches).",
        f"- Classification buckets: `{json.dumps(dict(bucket_counts), sort_keys=True)}`",
        "",
        "## Phase 1 outputs",
        "",
        "- `docs/migration/phase1_graphs.json` — folder import hints, OpenAPI routes, ORM tables from `database/models.py`.",
        "",
        "## Phase 2 outputs",
        "",
        "- `docs/migration/phase2_classification.json` — heuristic single-bucket label per file.",
        "",
        "## Caveats",
        "",
        "- Heuristic classification is not legal/compliance advice; review edge files manually.",
        "",
    ]
    (OUT / "MIGRATION_REPORT_AUTO.md").write_text("\n".join(report), encoding="utf-8")
    print(f"Wrote {OUT / 'phase1_graphs.json'}, phase2_classification.json, MIGRATION_REPORT_AUTO.md")


if __name__ == "__main__":
    main()
