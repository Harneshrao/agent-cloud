#!/usr/bin/env python3
"""
Remove all users and all user-related data from the database (sessions, refresh tokens,
api_keys, project_members, teams, projects, workflow templates, etc.).
After running, the platform has zero users — no stored emails/Gmail IDs.

Run from project root:
  py -3.11 scripts/clear_all_users.py
  or:  python scripts/clear_all_users.py
"""

import os
import sys

# Project root on path
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
os.chdir(_root)

from database.users import clear_all_user_data

if __name__ == "__main__":
    n = clear_all_user_data()
    print(f"Cleared all user data. Removed {n} user(s). Database now has zero users.")
