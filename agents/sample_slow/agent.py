"""Short sleep — observe execution_ms in usage and task trace."""

import time


class Agent:
    def run(self, state: dict) -> dict:
        seconds = min(int(state.get("sleep_seconds", 3)), 30)
        time.sleep(seconds)
        return {"slept_seconds": seconds, "agent": "sample_slow"}
