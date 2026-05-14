"""System / health extensions."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/version")
def version() -> dict[str, str]:
    import agent_cloud

    return {"package": "agent_cloud", "version": getattr(agent_cloud, "__version__", "0")}
