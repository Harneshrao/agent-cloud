"""Verify Alembic head matches database before serving traffic."""

from __future__ import annotations

import os
from pathlib import Path
from typing import List

# Wave 1 tables required for unassisted alpha sessions
WAVE1_REQUIRED_TABLES = (
    "regions",
    "api_keys",
    "agent_deployments",
    "agent_artifacts",
    "tasks",
    "product_events",
)


def get_head_revision() -> str:
    """Resolve Alembic head from repo scripts (lazy-imports alembic)."""
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory
    except ModuleNotFoundError as e:
        raise RuntimeError(
            "Alembic is not installed. Install project deps: pip install -r requirements.txt "
            "or: pip install alembic. To skip this check locally, set SKIP_MIGRATION_CHECK=1."
        ) from e

    root = Path(__file__).resolve().parents[1]
    ini = root / "alembic.ini"
    cfg = Config(str(ini))
    script = ScriptDirectory.from_config(cfg)
    heads = script.get_heads()
    if not heads:
        raise RuntimeError("No Alembic heads found")
    if len(heads) > 1:
        raise RuntimeError("Multiple Alembic heads; resolve branches before deploy")
    return heads[0]


def get_db_revision() -> str | None:
    """Read current revision from DB (lazy-imports SQLAlchemy + engine)."""
    try:
        from sqlalchemy import text
        from sqlalchemy.exc import OperationalError

        from database.session import engine
    except ModuleNotFoundError as e:
        raise RuntimeError(
            "SQLAlchemy is not installed (or database stack incomplete). "
            "Install: pip install -r requirements.txt. "
            "To skip migration check locally, set SKIP_MIGRATION_CHECK=1."
        ) from e

    try:
        with engine.connect() as conn:
            row = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
            if row is None:
                return None
            return str(row[0])
    except OperationalError as e:
        raise RuntimeError(
            "Cannot connect to PostgreSQL for migration check. "
            "Set DATABASE_URL in .env or the environment (see .env.example), then run "
            "`alembic upgrade head`. "
            "To skip only this check: SKIP_MIGRATION_CHECK=1 "
            "(API routes that use the DB will still need a working DATABASE_URL)."
        ) from e


def missing_required_tables(tables: tuple[str, ...] | None = None) -> List[str]:
    """Return table names that are absent from public schema."""
    names = tables or WAVE1_REQUIRED_TABLES
    try:
        from sqlalchemy import text

        from database.session import engine
    except ModuleNotFoundError as e:
        raise RuntimeError("SQLAlchemy not installed") from e

    missing: List[str] = []
    with engine.connect() as conn:
        for table in names:
            row = conn.execute(
                text("SELECT to_regclass(:name)"),
                {"name": f"public.{table}"},
            ).fetchone()
            if row is None or row[0] is None:
                missing.append(table)
    return missing


def assert_migrations_applied() -> None:
    if os.environ.get("SKIP_MIGRATION_CHECK", "").strip().lower() in ("1", "true", "yes"):
        return
    head = get_head_revision()
    db_rev = get_db_revision()
    if db_rev != head:
        raise RuntimeError(
            f"Database migrations are not at head: alembic_version={db_rev!r}, "
            f"expected {head!r}. Run: alembic upgrade head"
        )
    missing = missing_required_tables()
    if missing:
        raise RuntimeError(
            f"Database schema incomplete — missing tables: {', '.join(missing)}. "
            "Run: alembic upgrade head"
        )
