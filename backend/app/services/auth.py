from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import Tenant, User


pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
settings = get_settings()


class AuthError(Exception):
    pass


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(user: User) -> tuple[str, int]:
    expire_delta = timedelta(minutes=settings.jwt_access_token_expire_minutes)
    expires_at = datetime.now(UTC) + expire_delta
    payload = {
        "sub": str(user.id),
        "tenant_id": str(user.tenant_id),
        "role": user.role,
        "exp": expires_at,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, int(expire_delta.total_seconds())


def decode_access_token(token: str) -> dict[str, str]:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise AuthError("invalid token") from exc


async def register_user(
    session: AsyncSession,
    email: str,
    password: str,
    tenant_name: str,
    name: str | None,
) -> User:
    existing = await session.scalar(select(User).where(User.email == email))
    if existing:
        raise AuthError("email already exists")

    tenant = Tenant(name=tenant_name)
    user = User(
        email=email,
        password_hash=hash_password(password),
        name=name,
        tenant=tenant,
        role="owner",
    )
    session.add_all([tenant, user])
    await session.commit()
    await session.refresh(user)
    return user


async def authenticate_user(session: AsyncSession, email: str, password: str) -> User:
    user = await session.scalar(select(User).where(User.email == email))
    if not user or not verify_password(password, user.password_hash):
        raise AuthError("invalid credentials")
    return user


async def get_user_by_id(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await session.get(User, user_id)
