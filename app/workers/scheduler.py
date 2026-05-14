"""
Scheduler entrypoint (ZSET promotion + visibility recovery):

  python -m app.workers.scheduler
"""

from __future__ import annotations


def main() -> None:
    from workers.scheduler_runner import main as run

    run()


if __name__ == "__main__":
    main()
