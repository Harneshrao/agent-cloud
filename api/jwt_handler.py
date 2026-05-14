from datetime import datetime, timedelta
import os
import uuid

from jose import jwt

SECRET_KEY = os.getenv("JWT_SECRET", "agent-cloud-secret")
ALGORITHM = "HS256"


def create_access_token(user_id: uuid.UUID) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.utcnow() + timedelta(hours=24),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
