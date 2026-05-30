from app.services.agent_runner import AgentResult


def verify_result(result: AgentResult) -> bool:
    """
    Minimal verification gate.
    Returns True only if the agent reported success and produced non-empty output.
    Extend this later: schema checks, confidence scores, tool-call validation, etc.
    """
    if not result.success:
        return False
    if not result.output or len(result.output.strip()) < 3:
        return False
    return True
