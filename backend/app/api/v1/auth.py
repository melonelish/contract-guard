from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.exceptions import APIException
from app.schemas.api import (
    APIResponse,
    AuthTokenPayload,
    LoginRequest,
    RegisterRequest,
    UserPayload,
)
from app.schemas.errors import ErrorCode
from app.services.auth import AuthError, authenticate_user, create_access_token, register_user

router = APIRouter()


@router.post("/register", response_model=APIResponse[AuthTokenPayload], status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    session: AsyncSession = Depends(get_db),
) -> APIResponse[AuthTokenPayload]:
    try:
        user = await register_user(
            session=session,
            email=payload.email,
            password=payload.password,
            tenant_name=payload.tenant_name,
            name=payload.name,
        )
    except AuthError as exc:
        raise APIException(ErrorCode.CONFLICT, "conflict", False) from exc

    token, expires_in = create_access_token(user)
    return APIResponse(
        data=AuthTokenPayload(
            access_token=token,
            expires_in=expires_in,
            user=UserPayload.model_validate(user),
        )
    )


@router.post("/login", response_model=APIResponse[AuthTokenPayload])
async def login(
    payload: LoginRequest,
    session: AsyncSession = Depends(get_db),
) -> APIResponse[AuthTokenPayload]:
    try:
        user = await authenticate_user(session, payload.email, payload.password)
    except AuthError as exc:
        raise APIException(ErrorCode.UNAUTHORIZED, "unauthorized", False) from exc

    token, expires_in = create_access_token(user)
    return APIResponse(
        data=AuthTokenPayload(
            access_token=token,
            expires_in=expires_in,
            user=UserPayload.model_validate(user),
        )
    )


@router.get("/me", response_model=APIResponse[UserPayload])
async def me(current_user=Depends(get_current_user)) -> APIResponse[UserPayload]:
    return APIResponse(data=UserPayload.model_validate(current_user))
