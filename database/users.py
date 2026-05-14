"""Users — PostgreSQL UUID primary keys only (Alembic schema)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from database.models import User
from database.session import SessionLocal


def create_user(name: str, email: str, password_hash: str) -> Dict[str, Any]:
    with SessionLocal() as session:
        u = User(
            email=email.lower(),
            password_hash=password_hash,
            name=name.strip() or None,
        )
        session.add(u)
        session.commit()
        session.refresh(u)
        return _user_to_dict(u)


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    with SessionLocal() as session:
        u = session.execute(
            select(User).where(User.email == email.lower())
        ).scalar_one_or_none()
        return _user_to_dict(u) if u else None


def get_user_by_id(user_id: uuid.UUID) -> Optional[Dict[str, Any]]:
    with SessionLocal() as session:
        u = session.get(User, user_id)
        return _user_to_dict(u) if u else None


def update_user_name(user_id: uuid.UUID, name: str) -> None:
    with SessionLocal() as session:
        session.execute(
            update(User).where(User.id == user_id).values(name=name.strip())
        )
        session.commit()


def _user_to_dict(u: User) -> Dict[str, Any]:
    return {
        "id": u.id,
        "email": u.email,
        "password_hash": u.password_hash,
        "name": u.name,
        "created_at": u.created_at,
    }
