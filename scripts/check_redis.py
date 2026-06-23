#!/usr/bin/env python3
"""
Redis deep health — ping, set/get, BRPOP smoke test.

Usage:
  py -3.11 scripts/check_redis.py

Exit 0 = PASS, 1 = FAIL
"""

from __future__ import annotations

import os
import sys
import time

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)


def run_checks() -> tuple[bool, list[str]]:
    lines: list[str] = []
    ok = True

    try:
        from redis_queue_pkg.redis_client import make_redis_client, normalize_redis_url
        from config.settings import REDIS_URL

        url = normalize_redis_url(REDIS_URL)
        lines.append(f"REDIS_URL={url}")

        client = make_redis_client(url)

        if not client.ping():
            lines.append("FAIL ping")
            return False, lines
        lines.append("PASS ping")

        token = f"health-{int(time.time())}"
        client.set("healthcheck:ping", token, ex=30)
        got = client.get("healthcheck:ping")
        if got != token:
            lines.append(f"FAIL set/get (expected {token!r}, got {got!r})")
            ok = False
        else:
            lines.append("PASS set/get")

        test_list = "queue:healthcheck:brpop"
        client.delete(test_list)
        client.lpush(test_list, "ok")
        item = client.brpop(test_list, timeout=2)
        if not item or item[1] != "ok":
            lines.append(f"FAIL BRPOP (got {item!r})")
            ok = False
        else:
            lines.append("PASS BRPOP timeout")

        from redis_queue_pkg.redis_queue import get_task_queue

        depth = get_task_queue().queue_depth_ready()
        lines.append(f"PASS queue ready depth={depth}")

    except Exception as exc:
        lines.append(f"FAIL {exc}")
        ok = False

    lines.insert(0, "PASS Redis" if ok else "FAIL Redis")
    return ok, lines


def main() -> int:
    ok, lines = run_checks()
    for line in lines:
        print(line)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
