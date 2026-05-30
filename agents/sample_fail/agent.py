"""Fails on first runs — use to teach retries and DLQ."""


class Agent:
    def run(self, state: dict) -> dict:
        attempt = int(state.get("_attempt", 0)) + 1
        if attempt < 2:
            raise RuntimeError(
                "Intentional failure (sample_fail). Retry will succeed on attempt 2."
            )
        return {"recovered": True, "attempt": attempt}
