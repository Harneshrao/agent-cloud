"""
Development helper: ensure Alembic migrations are applied.

Usage: python scripts/init_db.py
"""

from __future__ import annotations

import subprocess
import sys


def main() -> None:
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)


if __name__ == "__main__":
    main()
