"""
Fast component health probes — used by GET /health?deep=1 and dev doctor scripts.

Each probe is timeout-bounded and must not raise into callers.
"""

from __future__ import annotations

import os
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from typing import Any, Callable, Dict, Tuple

DEFAULT_PROBE_TIMEOUT = 3.0


def _run_bounded(fn: Callable[[], Any], timeout: float = DEFAULT_PROBE_TIMEOUT) -> Tuple[bool, str]:
    with ThreadPoolExecutor(max_workers=1) as pool:
        fut = pool.submit(fn)
        try:
            result = fut.result(timeout=timeout)
            if isinstance(result, tuple) and len(result) == 2:
                return bool(result[0]), str(result[1])
            return True, "ok"
        except FuturesTimeout:
            return False, f"timeout after {timeout}s"
        except Exception as exc:
            return False, str(exc)[:200]


def probe_postgres() -> Tuple[bool, str]:
    from config.settings import DATABASE_URL

    def _ping() -> Tuple[bool, str]:
        import psycopg2

        conn = psycopg2.connect(DATABASE_URL, connect_timeout=2)
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()
            return True, "ok"
        finally:
            conn.close()

    return _run_bounded(_ping)


def probe_redis() -> Tuple[bool, str]:
    from config.settings import REDIS_URL

    def _ping() -> Tuple[bool, str]:
        import redis

        client = redis.from_url(REDIS_URL, socket_connect_timeout=2, socket_timeout=2)
        client.ping()
        return True, "ok"

    return _run_bounded(_ping)


def probe_workers(within_seconds: int = 60) -> Tuple[bool, str]:
    def _count() -> Tuple[bool, str]:
        from database.workers import count_active_workers

        n = count_active_workers(within_seconds=within_seconds)
        if n > 0:
            return True, f"{n} active"
        return False, "no heartbeat in last 60s"

    return _run_bounded(_count)


def probe_migrations() -> Tuple[bool, str]:
    """Alembic head + Wave 1 required tables."""
    def _check() -> Tuple[bool, str]:
        from api.migration_check import (
            get_db_revision,
            get_head_revision,
            missing_required_tables,
        )

        try:
            head = get_head_revision()
            db_rev = get_db_revision()
            if db_rev != head:
                return False, f"drift: db={db_rev!r} head={head!r}"
            missing = missing_required_tables()
            if missing:
                return False, f"missing: {', '.join(missing)}"
            return True, f"head={head}"
        except RuntimeError as e:
            return False, str(e)[:160]

    return _run_bounded(_check)


def component_status(
    *,
    include_workers: bool = True,
    worker_within_seconds: int = 60,
) -> Dict[str, str]:
    """Return {component: ok|detail} for deep health."""
    out: Dict[str, str] = {}

    ok, detail = probe_postgres()
    out["postgres"] = "ok" if ok else detail

    ok, detail = probe_redis()
    out["redis"] = "ok" if ok else detail

    if include_workers:
        ok, detail = probe_workers(within_seconds=worker_within_seconds)
        out["workers"] = "ok" if ok else detail

    ok, detail = probe_migrations()
    out["schema"] = "ok" if ok else detail

    return out


def overall_status(components: Dict[str, str]) -> str:
    if all(v == "ok" for v in components.values()):
        return "ok"
    if any(v != "ok" for v in components.values()):
        return "degraded"
    return "ok"
