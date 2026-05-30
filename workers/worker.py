"""
Compatibility shim — historical import path for the production worker.

The canonical loop is ``workers.guaranteed_loop``; execution body is
``workers.agent_executor.run``. Start via:

  python -m workers.canonical_worker
  python -m app.workers.worker
"""

from __future__ import annotations


def main() -> None:
    from workers.canonical_worker import main as run

    run()


if __name__ == "__main__":
    main()
