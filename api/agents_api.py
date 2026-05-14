from fastapi import APIRouter
from pydantic import BaseModel
from registry.agent_registry import agent_registry

router = APIRouter()


class AgentRegistration(BaseModel):
    name: str
    description: str
    capabilities: list


@router.post("/agents/register")
def register_agent(data: AgentRegistration):

    agent_registry.agents[data.name] = {
        "name": data.name,
        "description": data.description,
        "capabilities": data.capabilities
    }

    return {
        "status": "registered",
        "agent": data.name
    }


@router.get("/agents")
def list_agents():

    return {
        "agents": list(agent_registry.agents.keys())
    }