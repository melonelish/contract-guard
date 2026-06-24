from __future__ import annotations

import uuid

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import APIException
from app.db.session import get_db_session
from app.schemas.errors import ErrorCode
from app.services.auth import AuthError, decode_access_token, get_user_by_id

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_db() -> AsyncSession:
    async for session in get_db_session():
        yield session


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db),
):
    try:
        payload = decode_access_token(token)
        user_id = uuid.UUID(payload["sub"])
    except (AuthError, KeyError, ValueError) as exc:
        raise APIException(ErrorCode.UNAUTHORIZED, "unauthorized", False) from exc

    user = await get_user_by_id(session, user_id)
    if not user:
        raise APIException(ErrorCode.UNAUTHORIZED, "unauthorized", False)
    return user
