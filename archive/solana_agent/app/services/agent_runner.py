from dataclasses import dataclass

from openai import AsyncOpenAI

from app.core.config import settings

_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

SYSTEM_PROMPT = """\
You are a precise task-execution agent.
Given a task, complete it and return ONLY the result — no preamble, no explanation.
If the task cannot be completed, reply with: ERROR: <reason>
"""


@dataclass
class AgentResult:
    success: bool
    output: str


async def run_agent(task_input: str) -> AgentResult:
    """
    Send task_input to OpenAI and return a structured result.
    Raises on network/API errors so the orchestrator can catch and mark failed.
    """
    response = await _client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": task_input},
        ],
        temperature=0,
        max_tokens=1024,
    )

    output = response.choices[0].message.content or ""
    output = output.strip()

    if output.startswith("ERROR:"):
        return AgentResult(success=False, output=output)

    return AgentResult(success=True, output=output)
