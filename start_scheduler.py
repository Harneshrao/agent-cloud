"""
Entrypoint to run the unified scheduler supervisor from the project root.

Usage: python start_scheduler.py

Runs Redis ZSET promotion + visibility recovery (scheduler_runner) and
cron-based enqueue (scheduler_service) in one process.
"""

from workers.runtime_supervisor import main

if __name__ == "__main__":
    print("Starting runtime supervisor (Redis promoter + cron enqueue)...")
    main()
