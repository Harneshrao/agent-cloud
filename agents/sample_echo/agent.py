"""Sample echo agent — sync entrypoint for deployment runtime (onboarding)."""


class Agent:
    """Minimal agent: echoes input message in the result."""

    def run(self, state: dict) -> dict:
        message = (
            state.get("message")
            or state.get("task")
            or (state.get("input") or {}).get("message")
            or "hello"
        )
        if isinstance(message, dict):
            message = str(message)
        message = str(message).strip()
        return {
            "echo": message,
            "agent": "sample_echo",
            "ok": True,
        }
