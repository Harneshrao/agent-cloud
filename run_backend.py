#!/usr/bin/env python3
"""Start the Agent Cloud FastAPI backend on http://127.0.0.1:8000"""
import sys

if sys.version_info[:2] != (3, 11):
    print("")
    print("Agent Cloud requires Python 3.11")
    print("Current version:", sys.version)
    print("Run using:")
    print("py -3.11 run_backend.py")
    print("")
    sys.exit(1)

try:
    from jose import jwt  # type: ignore[unused-import]
except ImportError:
    print("")
    print("Missing dependency: python-jose")
    print("Fix it by running:")
    print("pip install python-jose[cryptography]")
    print("")
    raise

import os
import socket
import uvicorn

# So the dashboard (no auth) can call the API when running locally
os.environ.setdefault("ALLOW_ANONYMOUS_DEV", "1")


def apply_skip_migration_if_no_alembic() -> None:
    """If Alembic is missing, set SKIP_MIGRATION_CHECK=1 (migration check only)."""
    if os.environ.get("SKIP_MIGRATION_CHECK"):
        return
    try:
        import alembic  # noqa: F401
    except ImportError:
        os.environ["SKIP_MIGRATION_CHECK"] = "1"
        print(
            "[run_backend] Alembic not installed — SKIP_MIGRATION_CHECK=1. "
            "Install: pip install -r requirements.txt\n",
            flush=True,
        )


def require_sqlalchemy_or_exit() -> None:
    """
    The API imports database models on startup; SQLAlchemy is mandatory.
    Call this before uvicorn.run().
    """
    try:
        import sqlalchemy  # noqa: F401
    except ImportError:
        print("")
        print("ERROR: SQLAlchemy is not installed. The API cannot start without it.")
        print("")
        print("  pip install -r requirements.txt")
        print("")
        print("Or at minimum:")
        print("  pip install sqlalchemy psycopg2-binary")
        print("")
        sys.exit(1)


def warn_if_migration_drift() -> None:
    """Print startup warning when DB is behind Alembic head or missing Wave 1 tables."""
    if os.environ.get("SKIP_MIGRATION_CHECK", "").strip().lower() in ("1", "true", "yes"):
        return
    try:
        from api.migration_check import (
            get_db_revision,
            get_head_revision,
            missing_required_tables,
        )

        head = get_head_revision()
        db_rev = get_db_revision()
        missing = missing_required_tables()
        if db_rev == head and not missing:
            return
        print("")
        print("[run_backend] WARNING — database not ready for Wave 1 alpha testers:")
        if db_rev != head:
            print(f"  • Alembic drift: db={db_rev!r} head={head!r}")
        if missing:
            print(f"  • Missing tables: {', '.join(missing)}")
        print("  Fix: alembic upgrade head")
        print("")
    except Exception as exc:
        print(f"\n[run_backend] WARNING — migration check failed: {exc}\n", flush=True)


apply_skip_migration_if_no_alembic()


def _port_in_use(port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("0.0.0.0", port))
        return False
    except OSError:
        return True

if __name__ == "__main__":
    require_sqlalchemy_or_exit()
    warn_if_migration_drift()

    # 0.0.0.0 so both localhost and 127.0.0.1 work (avoids IPv6 localhost vs IPv4 server mismatch)
    # In Docker, set DISABLE_RELOAD=1 to avoid file watcher issues and reduce CPU
    import argparse
    p = argparse.ArgumentParser(description="Start Agent Cloud API")
    p.add_argument("--no-reload", action="store_true", help="Disable reload (single process; can fix connection timeouts on Windows)")
    p.add_argument("--port", type=int, default=8000, help="Port to bind (default 8000)")
    args, _ = p.parse_known_args()
    # On Windows, default to no-reload to avoid WatchFiles spawn crashes on file change
    use_reload = (
        not args.no_reload
        and os.name != "nt"
        and os.environ.get("DISABLE_RELOAD", "").lower() not in ("1", "true", "yes")
    )
    port = args.port

    # Decide port before uvicorn (so fallback works even with reload)
    if port == 8000 and _port_in_use(8000):
        port = 8001
        use_reload = False
        print("Port 8000 is in use. Using port 8001 instead.")
        print(f"  API: http://127.0.0.1:{port}")
        print(f"  API docs (Swagger): http://127.0.0.1:{port}/docs")
        print(f"  Dashboard: $env:API_UPSTREAM=\"http://127.0.0.1:{port}\"; npm run dev")

    try:
        uvicorn.run(
            "api.main:app",
            host="0.0.0.0",
            port=port,
            reload=use_reload,
        )
    except OSError as e:
        if e.errno == 10048 and port == 8000:
            port = 8001
            use_reload = False
            print("Port 8000 is in use. Using port 8001 instead.")
            print(f"  API: http://127.0.0.1:{port}")
            print(f"  API docs (Swagger): http://127.0.0.1:{port}/docs")
            print(f"  Dashboard: $env:API_UPSTREAM=\"http://127.0.0.1:{port}\"; npm run dev")
            uvicorn.run(
                "api.main:app",
                host="0.0.0.0",
                port=port,
                reload=use_reload,
            )
        else:
            raise
