#!/usr/bin/env python3
"""
Legacy helper: removed SQLite file agent_cloud.db if present.

The platform now uses PostgreSQL (DATABASE_URL). To reset dev data:

  psql "$DATABASE_URL" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

Or recreate the database in Docker / RDS. Then restart the API so tables are
recreated via database.db + _ensure_schema hooks.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_FILE = PROJECT_ROOT / "agent_cloud.db"
DB_WAL = PROJECT_ROOT / "agent_cloud.db-wal"
DB_SHM = PROJECT_ROOT / "agent_cloud.db-shm"


def main() -> int:
    removed = []
    for f in (DB_FILE, DB_WAL, DB_SHM):
        if f.exists():
            try:
                f.unlink()
                removed.append(f.name)
            except OSError as e:
                print(f"Could not remove {f}: {e}", file=sys.stderr)
                return 1
    if removed:
        print(f"Removed legacy SQLite files: {', '.join(removed)}")
    else:
        print("No legacy agent_cloud.db files found. Use PostgreSQL to reset schema (see docstring).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
