"""
Scheduler entrypoint (Redis promoter + cron enqueue):

  python -m app.workers.scheduler
"""

from __future__ import annotations


def main() -> None:
    from workers.runtime_supervisor import main as run

    run()


if __name__ == "__main__":
    main()
