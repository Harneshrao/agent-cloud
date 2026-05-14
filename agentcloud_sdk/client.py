from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Optional, TypedDict

import requests


class RunAgentResponse(TypedDict):
  status: str
  task_id: int
  agent: str
  task: str


@dataclass
class ClientConfig:
  """
  Configuration for the Agent Cloud API client.
  """

  api_key: str
  base_url: str = "http://127.0.0.1:8000"
  project_id: Optional[int] = 1
  timeout: float = 10.0


class Client:
  """
  Minimal Python SDK client for Agent Cloud.

  Example:

      from agentcloud import Client

      client = Client(api_key="xxx")
      result = client.run_agent(
          agent_name="competitor-intelligence",
          input={"company": "Tesla"},
      )
      print(result)
  """

  def __init__(
      self,
      api_key: str,
      base_url: str = "http://127.0.0.1:8000",
      project_id: Optional[int] = 1,
      timeout: float = 10.0,
  ) -> None:
    self._config = ClientConfig(
        api_key=api_key,
        base_url=base_url.rstrip("/"),
        project_id=project_id,
        timeout=timeout,
    )

  @property
  def base_url(self) -> str:
    return self._config.base_url

  def _headers(self) -> Dict[str, str]:
    headers: Dict[str, str] = {
        "Authorization": f"Bearer {self._config.api_key}",
        "Content-Type": "application/json",
    }
    if self._config.project_id is not None:
      headers["X-Project-ID"] = str(self._config.project_id)
    return headers

  def run_agent(
      self,
      agent_name: str,
      input: Dict[str, Any],
      *,
      region: Optional[str] = None,
  ) -> RunAgentResponse:
    """
    Enqueue an agent run via POST /agent/run and return the structured response.

    The `input` dict is serialized into the `task` field as JSON so the
    underlying agent can parse it as needed.
    """
    payload: Dict[str, Any] = {
        "agent": agent_name,
        "task": json.dumps({"input": input}),
    }
    if region is not None:
      payload["region"] = region

    response = requests.post(
        f"{self.base_url}/agent/run",
        headers=self._headers(),
        json=payload,
        timeout=self._config.timeout,
    )
    response.raise_for_status()
    data = response.json()

    return RunAgentResponse(
        status=str(data.get("status", "")),
        task_id=int(data.get("task_id")),
        agent=str(data.get("agent", "")),
        task=str(data.get("task", "")),
    )

