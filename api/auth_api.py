import os
import uuid
from typing import Any, Dict

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel

from api.jwt_handler import create_access_token, decode_token
from api.security import hash_password, validate_password, verify_password
from config.settings import DEFAULT_USER_UUID
from database.api_keys import PREFIX as API_KEY_PREFIX
from database.api_keys import get_user_by_key
from database.users import create_user, get_user_by_email, get_user_by_id

router = APIRouter(tags=["auth"])


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterResponse(BaseModel):
    id: uuid.UUID
    email: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    id: uuid.UUID
    email: str
    name: str | None = None


@router.post("/register", response_model=RegisterResponse)
def register(data: RegisterRequest) -> Dict[str, Any]:
    email = data.email.strip().lower()
    password = data.password

    try:
        validate_password(password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if get_user_by_email(email) is not None:
        raise HTTPException(status_code=400, detail="Email already registered")

    password_hash = hash_password(password)
    user = create_user(data.name.strip(), email, password_hash)
    try:
        from services.product_analytics import track_signup

        track_signup(user["id"], email=email)
    except Exception:
        pass

    return {"id": user["id"], "email": user["email"]}


@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest) -> Dict[str, Any]:
    email = data.email.strip().lower()
    password = data.password

    user = get_user_by_email(email)
    if user is None or not verify_password(password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    try:
        from services.product_analytics import track_login

        track_login(user["id"])
    except Exception:
        pass
    token = create_access_token(user["id"])
    return {"access_token": token, "token_type": "bearer"}


def get_current_user(
    request: Request,
    authorization: str | None = Header(None, alias="Authorization"),
) -> Dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        if os.environ.get("ALLOW_ANONYMOUS_DEV", "").strip().lower() in ("1", "true", "yes"):
            return {
                "id": uuid.UUID(DEFAULT_USER_UUID),
                "email": "dev@local",
                "name": "Dev User",
            }
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")

    if token.startswith(API_KEY_PREFIX):
        user = get_user_by_key(token)
        if user is None:
            raise HTTPException(status_code=401, detail="Invalid API key")
        return user

    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    try:
        user_id = uuid.UUID(str(user_id_str))
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return user


def get_current_user_optional(request: Request):
    auth_header = request.headers.get("Authorization")

    if not auth_header:
        return None

    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header.replace("Bearer ", "").strip()

    try:
        payload = decode_token(token)
        user_id = uuid.UUID(str(payload.get("sub")))
        return get_user_by_id(user_id)
    except (ValueError, TypeError, Exception):
        return None


@router.get("/me", response_model=MeResponse)
def me(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    return {"id": user["id"], "email": user["email"], "name": user.get("name")}
