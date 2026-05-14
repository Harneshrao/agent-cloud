#!/usr/bin/env python3
"""
Schema drift audit: compare signals from Alembic, SQLAlchemy models, and runtime DDL hooks.

Outputs Markdown to stdout or --out. Heuristics only — human review required.

Checks:
  1. Table names referenced in alembic/versions/*.py (op.create_table, create_table strings).
  2. __tablename__ in database/models.py.
  3. database/*.py files whose _ensure_schema() body still contains CREATE TABLE (drift risk).
  4. database/*.py files defining _ensure_schema (count of modules still calling runtime init).

Usage:
  python scripts/schema_drift_audit.py
  python scripts/schema_drift_audit.py --out docs/generated/schema_drift_audit.md
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def extract_alembic_table_names(versions_dir: Path) -> set[str]:
    pat = re.compile(r"""create_table\s*\(\s*['"]([a-zA-Z0-9_]+)['"]""")
    text_pat = re.compile(
        r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:public\.)?['\"]?([a-zA-Z0-9_]+)['\"]?",
        re.IGNORECASE,
    )
    sql_noise = frozenset(
        {
            "with",
            "without",
            "as",
            "on",
            "to",
            "or",
            "and",
            "not",
            "null",
            "default",
            "constraint",
            "primary",
            "unique",
            "check",
            "foreign",
            "references",
        }
    )
    found: set[str] = set()
    for path in sorted(versions_dir.glob("*.py")):
        text = path.read_text(encoding="utf-8", errors="replace")
        for m in pat.finditer(text):
            name = m.group(1)
            if name.lower() not in sql_noise:
                found.add(name)
        for m in text_pat.finditer(text):
            name = m.group(1)
            if name.lower() not in sql_noise:
                found.add(name)
    return found


def extract_sqlalchemy_tablenames(models_path: Path) -> set[str]:
    return {p["__tablename__"] for p in extract_sqlalchemy_model_pairs(models_path)}


def extract_sqlalchemy_model_pairs(models_path: Path) -> list[dict]:
    pairs: list[dict] = []
    tree = ast.parse(models_path.read_text(encoding="utf-8"), filename=str(models_path))
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        for sub in node.body:
            if not isinstance(sub, ast.Assign):
                continue
            for t in sub.targets:
                if isinstance(t, ast.Name) and t.id == "__tablename__":
                    if isinstance(sub.value, ast.Constant) and isinstance(sub.value.value, str):
                        pairs.append({"class": node.name, "__tablename__": sub.value.value})
                    break
    return pairs


def extract_alembic_revisions(versions_dir: Path) -> list[dict]:
    rev_line = re.compile(r"""revision:\s*str\s*=\s*['"]([^'"]+)['"]""")
    down_line = re.compile(r"down_revision:\s*[^=]+=\s*(.+)")
    revs: list[dict] = []
    for p in sorted(versions_dir.glob("*.py")):
        t = p.read_text(encoding="utf-8", errors="replace")
        m = rev_line.search(t)
        d = down_line.search(t)
        rev = m.group(1) if m else None
        down: str | list[str] | None = None
        if d:
            raw = d.group(1).split("#")[0].strip().rstrip(",")
            if raw.startswith("None"):
                down = None
            else:
                q = re.findall(r"['\"]([^'\"]+)['\"]", raw)
                if len(q) > 1:
                    down = q
                elif len(q) == 1:
                    down = q[0]
                else:
                    down = raw
        revs.append({"file": p.name, "revision": rev, "down_revision": down})
    return revs


def analyze_ensure_schema(database_dir: Path) -> tuple[list[str], list[str]]:
    with_create: list[str] = []
    all_with: list[str] = []
    for path in sorted(database_dir.glob("*.py")):
        text = path.read_text(encoding="utf-8", errors="replace")
        if "def _ensure_schema" not in text:
            continue
        all_with.append(path.name)
        if re.search(r"CREATE\s+TABLE", text, re.IGNORECASE):
            with_create.append(path.name)
    return with_create, all_with


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Write Markdown report to this path",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Also write machine-readable schema inventory (JSON)",
    )
    args = parser.parse_args()
    root = _repo_root()
    alembic_tables = extract_alembic_table_names(root / "alembic" / "versions")
    models_path = root / "database" / "models.py"
    model_tables = extract_sqlalchemy_tablenames(models_path)
    model_pairs = extract_sqlalchemy_model_pairs(models_path)
    create_in_modules, ensure_modules = analyze_ensure_schema(root / "database")
    alembic_revs = extract_alembic_revisions(root / "alembic" / "versions")

    in_alembic_not_models = sorted(alembic_tables - model_tables)
    in_models_not_alembic = sorted(model_tables - alembic_tables)

    lines = [
        "# Schema drift audit (heuristic)",
        "",
        "## Summary counts",
        "",
        "| Source | Count |",
        "|--------|------:|",
        f"| Alembic-inferred table names | {len(alembic_tables)} |",
        f"| SQLAlchemy `__tablename__` in models.py | {len(model_tables)} |",
        f"| `database/*.py` with `_ensure_schema` | {len(ensure_modules)} |",
        f"| Same files containing `CREATE TABLE` string | {len(create_in_modules)} |",
        "",
        "## Alembic vs ORM model names (symmetric difference)",
        "",
        "### In Alembic scripts but not in `database/models.py` `__tablename__`",
        "",
    ]
    if in_alembic_not_models:
        lines.extend(f"- `{t}`" for t in in_alembic_not_models)
    else:
        lines.append("_None (under this heuristic)._")
    lines.extend(
        [
            "",
            "### In `database/models.py` but not matched in Alembic text scan",
            "",
        ]
    )
    if in_models_not_alembic:
        lines.extend(f"- `{t}`" for t in in_models_not_alembic)
    else:
        lines.append("_None (under this heuristic)._")

    lines.extend(
        [
            "",
            "## Runtime DDL risk (`CREATE TABLE` string still present)",
            "",
            "These `database/*.py` files still contain a `CREATE TABLE` substring. "
            "Prefer schema changes via Alembic only; see `tools/strip_runtime_ddl.py`.",
            "",
        ]
    )
    if create_in_modules:
        lines.extend(f"- `{n}`" for n in create_in_modules)
    else:
        lines.append("_None._")

    lines.extend(
        [
            "",
            "## All `database/*.py` defining `_ensure_schema`",
            "",
            f"_Total: {len(ensure_modules)} files._",
            "",
        ]
    )
    lines.extend(f"- `{n}`" for n in ensure_modules)
    lines.extend(
        [
            "",
            "## Limitations",
            "",
            "- Alembic table extraction misses dynamic names and `op.rename` / raw SQL edge cases.",
            "- Many tables exist only in raw `database/*.py` SQL strings; compare to `infra/postgres/schema.sql` manually.",
            "- This script does not connect to a live database.",
            "",
        ]
    )
    md = "\n".join(lines) + "\n"

    if args.json_out:
        payload = {
            "format": "agent-cloud.schema_inventory.v1",
            "alembic_versions": alembic_revs,
            "alembic_inferred_tables": sorted(alembic_tables),
            "sqlalchemy_models_database_models_py": model_pairs,
            "symmetric_diff": {
                "in_alembic_not_models": in_alembic_not_models,
                "in_models_not_alembic": in_models_not_alembic,
            },
            "database_py_with_create_table_substring": create_in_modules,
            "database_py_with_ensure_schema": ensure_modules,
            "solana_agent": {
                "async_metadata_create_all": "solana_agent/app/core/database.py:create_tables",
                "example_model": [{"class": "Task", "__tablename__": "tasks"}],
            },
        }
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Wrote {args.json_out}")

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(md, encoding="utf-8")
        print(f"Wrote {args.out}")
    else:
        print(md, end="")


if __name__ == "__main__":
    main()
