"""
Google OAuth2 (Authorization Code) login.

GET /auth/google/login  -> Redirect to Google consent.
GET /auth/google/callback -> Exchange code, get profile, find/create user, issue JWT + refresh; redirect to frontend with tokens.
"""

from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from api.jwt_handler import create_access_token
from security.ssrf import assert_url_allowed, safe_httpx_client
from database.users import (
    create_user_oauth,
    get_user_by_google_id,
    get_user_by_email,
    get_user_by_id_full,
    link_google_to_user,
)
from database.refresh_tokens import create_refresh_token, REFRESH_EXPIRATION_DAYS
from database.auth_sessions import create_session as create_auth_session

router = APIRouter(prefix="/auth", tags=["auth"])

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback").strip()
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000").strip().rstrip("/")

OAUTH_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
OAUTH_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

STATE_TTL_SEC = 300  # 5 min, single use
STATE_KEY_PREFIX = "oauth_state:"


def _get_redis():
    try:
        import redis
        url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        return redis.from_url(url, decode_responses=True)
    except Exception:
        return None


def _store_state(state: str) -> None:
    r = _get_redis()
    if r:
        r.setex(f"{STATE_KEY_PREFIX}{state}", STATE_TTL_SEC, "1")


def _consume_state(state: str) -> bool:
    r = _get_redis()
    if not r:
        return True  # no Redis: skip state check (dev only)
    key = f"{STATE_KEY_PREFIX}{state}"
    if not r.get(key):
        return False
    r.delete(key)
    return True


@router.get("/google/login")
def google_login(request: Request):
    """Redirect to Google OAuth consent screen. CSRF state stored in Redis."""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google OAuth not configured (GOOGLE_CLIENT_ID)")
    state = secrets.token_urlsafe(32)
    _store_state(state)
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
    }
    return RedirectResponse(url=f"{OAUTH_AUTH_URL}?{urlencode(params)}")


@router.get("/google/callback")
def google_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
):
    """Exchange code for tokens, fetch profile, find/create user, issue JWT + refresh; redirect to frontend with tokens."""
    if error:
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=access_denied")
    if not code or not state:
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=missing_code")
    if not _consume_state(state):
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=invalid_state")
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=server_config")

    assert_url_allowed(OAUTH_TOKEN_URL)
    assert_url_allowed(OAUTH_USERINFO_URL)
    with safe_httpx_client() as client:
        # Exchange code for tokens
        resp = client.post(
            OAUTH_TOKEN_URL,
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if resp.status_code != 200:
            return RedirectResponse(url=f"{FRONTEND_URL}/login?error=token_exchange")
        data = resp.json()
        access_token = data.get("access_token")
        if not access_token:
            return RedirectResponse(url=f"{FRONTEND_URL}/login?error=token_exchange")

        # Fetch user profile
        ui = client.get(
            OAUTH_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if ui.status_code != 200:
            return RedirectResponse(url=f"{FRONTEND_URL}/login?error=userinfo")
        profile = ui.json()
    email = (profile.get("email") or "").strip().lower()
    name = (profile.get("name") or "").strip() or None
    google_id = profile.get("id") or ""
    picture = profile.get("picture")
    if not email:
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=no_email")

    # Find or create user
    user = get_user_by_google_id(google_id)
    if user:
        pass
    else:
        existing = get_user_by_email(email)
        if existing:
            user = get_user_by_id_full(existing["id"])
            if user:
                link_google_to_user(user["id"], google_id, picture)
        if not user:
            try:
                user = create_user_oauth(email=email, name=name, google_id=google_id, avatar_url=picture)
            except ValueError:
                user = get_user_by_google_id(google_id) or get_user_by_id_full(
                    get_user_by_email(email)["id"]
                )
                if user and not user.get("google_id"):
                    link_google_to_user(user["id"], google_id, picture)

    if not user or user.get("status") != "active":
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=account_inactive")

    def _client_ip(req: Request) -> str:
        forwarded = req.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return req.client.host if req.client else ""
    def _user_agent(req: Request) -> str | None:
        return req.headers.get("User-Agent")

    access_token_jwt = create_access_token(user["id"])
    refresh_plain, token_row_id = create_refresh_token(user["id"])
    expires_at = datetime.utcnow() + timedelta(days=REFRESH_EXPIRATION_DAYS)
    create_auth_session(
        user["id"],
        token_row_id,
        expires_at,
        ip_address=_client_ip(request),
        user_agent=_user_agent(request),
    )
    user_safe = {k: v for k, v in user.items() if k != "password_hash"}

    # Redirect to frontend with tokens in query (frontend stores and redirects to dashboard)
    from urllib.parse import urlencode as q
    params = {
        "access_token": access_token_jwt,
        "refresh_token": refresh_plain,
        "user_id": str(user["id"]),
    }
    return RedirectResponse(url=f"{FRONTEND_URL}/auth/callback?{q(params)}")
