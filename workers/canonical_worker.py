"""
Canonical production worker entrypoint.

  python -m workers.canonical_worker
  python -m app.workers.worker   # same loop

Loop: ``workers.guaranteed_loop`` (dequeue → lock → claim → visibility → execute).
Body: ``workers.agent_executor.run`` (v2, pipeline, DAG).
"""

from __future__ import annotations

import os
import threading
import time
import uuid

from agent_runtime.loader import discover_agents

discover_agents()


def _register_worker() -> tuple[str, list[str] | None, str | None, str | None]:
    from engine.worker_registry import (
        get_capabilities,
        heartbeat,
        register_worker,
        set_capabilities,
    )

    worker_id = (os.environ.get("WORKER_ID") or "").strip()
    if not worker_id:
        worker_id = "worker-" + str(uuid.uuid4())[:8]
        os.environ["WORKER_ID"] = worker_id

    worker_region = os.environ.get("WORKER_REGION", "").strip() or None
    worker_type = (os.environ.get("WORKER_TYPE", "").strip() or "").lower() or None
    register_worker(worker_id, region=worker_region, worker_type=worker_type)

    caps_env = os.environ.get("WORKER_CAPABILITIES", "").strip()
    worker_capabilities = (
        [c.strip() for c in caps_env.split(",") if c.strip()] if caps_env else None
    )
    if worker_capabilities:
        set_capabilities(worker_id, worker_capabilities)

    def _heartbeat_loop() -> None:
        while True:
            time.sleep(10)
            try:
                caps = get_capabilities(worker_id)
                n = 1 if caps else 0
                heartbeat(worker_id, tasks_running=n, region=worker_region)
            except Exception:
                pass

    threading.Thread(target=_heartbeat_loop, daemon=True).start()
    return worker_id, worker_capabilities, worker_region, worker_type


def main() -> None:
    os.environ.setdefault("EXECUTOR_MODULE", "workers.agent_executor")
    os.environ.setdefault("EXECUTOR_CALLABLE", "run")

    _worker_id, caps, region, wtype = _register_worker()

    from workers.guaranteed_loop import main as loop_main

    # Filters read from env in loop_once via WORKER_* set above
    if caps is not None:
        os.environ["WORKER_CAPABILITIES"] = ",".join(caps)
    if region:
        os.environ["WORKER_REGION"] = region
    if wtype:
        os.environ["WORKER_TYPE"] = wtype

    loop_main()


if __name__ == "__main__":
    main()
