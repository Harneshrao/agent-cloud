"""
Entrypoint to run the scheduler service from the project root.

Usage: python start_scheduler.py

Calls the same logic as: python -m scheduler.scheduler_service
"""

from scheduler.scheduler_service import start_scheduler

if __name__ == "__main__":
    print("Starting scheduler (root entrypoint)...")
    start_scheduler()
