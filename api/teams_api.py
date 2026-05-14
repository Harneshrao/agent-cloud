"""
Teams API: list and create teams. Multi-tenant.

GET  /teams  - List teams for the current user (with role)
POST /teams  - Create a team (caller becomes owner)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from database.teams import create_team as db_create_team, list_teams_for_user
from api.auth_api import get_current_user

router = APIRouter(prefix="/teams", tags=["teams"])


class CreateTeamRequest(BaseModel):
    name: str = Field(..., min_length=1, description="Team name")


@router.get("")
def list_teams(user: dict = Depends(get_current_user)):
    """List all teams the current user is a member of."""
    teams = list_teams_for_user(user["id"])
    return {"teams": teams}


@router.post("")
def create_team(
    data: CreateTeamRequest,
    user: dict = Depends(get_current_user),
):
    """Create a team. The current user becomes the owner."""
    try:
        team = db_create_team(name=data.name.strip(), owner_user_id=user["id"])
        return {"team": team}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
