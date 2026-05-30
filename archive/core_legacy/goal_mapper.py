from typing import Dict


def map_goal_to_task(goal: str) -> Dict:
    goal_lower = goal.lower()

    if "landing page" in goal_lower:
        return {
            "agent": "research",
            "runtime": "v2",
            "input": {"task": goal},
        }

    if "marketing" in goal_lower:
        return {
            "agent": "strategy",
            "runtime": "v2",
            "input": {"task": goal},
        }

    if "content" in goal_lower:
        return {
            "agent": "content",
            "runtime": "v2",
            "input": {"task": goal},
        }

    # default fallback
    return {
        "agent": "research",
        "runtime": "v2",
        "input": {"task": goal},
    }

