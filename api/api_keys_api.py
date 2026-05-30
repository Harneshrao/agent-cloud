"""
API keys: create, list, delete.

POST   /api-keys     - Create key (name). Returns { id, key, name, created_at }. Key shown once.
GET    /api-keys     - List keys for current user (no plain key).
DELETE /api-keys/{id} - Revoke key.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.api_errors import error_detail
from api.auth_api import get_current_user
from database.api_keys import create_key, list_keys_for_user, delete_key

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


class CreateKeyBody(BaseModel):
    name: str = Field("API Key", description="Label for the key")


@router.post("")
def post_create_key(
    body: CreateKeyBody = CreateKeyBody(),
    user: dict = Depends(get_current_user),
):
    """Create an API key. The plain key is returned only once; store it securely."""
    try:
        key_meta = create_key(user["id"], body.name)
    except RuntimeError as e:
        raise HTTPException(
            status_code=503,
            detail=error_detail(
                "schema_not_ready",
                str(e),
                hint="Run: alembic upgrade head",
            ),
        ) from e
    try:
        from services.product_analytics import track

        from database import product_events as pe

        track(pe.EVENT_API_KEY_CREATED, user_id=user["id"], source="server")
    except Exception:
        pass
    return {
        "id": key_meta["id"],
        "key": key_meta["key"],
        "name": key_meta["name"],
        "created_at": key_meta["created_at"],
        "message": "Store the key securely; it will not be shown again.",
    }


@router.get("")
def get_api_keys(user: dict = Depends(get_current_user)):
    """List API keys for the current user (no plain key)."""
    try:
        keys = list_keys_for_user(user["id"])
    except RuntimeError as e:
        raise HTTPException(
            status_code=503,
            detail=error_detail(
                "schema_not_ready",
                str(e),
                hint="Run: alembic upgrade head",
            ),
        ) from e
    return {"api_keys": keys, "count": len(keys)}


@router.delete("/{key_id}")
def delete_api_key(key_id: int, user: dict = Depends(get_current_user)):
    """Revoke an API key. Only the owner can delete."""
    deleted = delete_key(key_id, user["id"])
    if not deleted:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"status": "deleted", "id": key_id}
