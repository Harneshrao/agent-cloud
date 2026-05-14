from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from core.war_room_engine import analyze_growth

router = APIRouter()


class WarRoomRequest(BaseModel):
    input: str


@router.post("/war-room/analyze")
def war_room(req: WarRoomRequest):
    return analyze_growth(req.input)

