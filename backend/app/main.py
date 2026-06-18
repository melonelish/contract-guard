from __future__ import annotations

import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette import status

from app.api.v1.router import router as api_router
from app.config import get_settings
from app.core.exceptions import APIException
from app.schemas.api import ErrorMeta, ErrorResponse
from app.schemas.errors import ErrorCode


settings = get_settings()


HTTP_CODE_MAP = {
    ErrorCode.INVALID_REQUEST: status.HTTP_400_BAD_REQUEST,
    ErrorCode.UNAUTHORIZED: status.HTTP_401_UNAUTHORIZED,
    ErrorCode.FORBIDDEN: status.HTTP_403_FORBIDDEN,
    ErrorCode.NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.CONFLICT: status.HTTP_409_CONFLICT,
    ErrorCode.RATE_LIMITED: status.HTTP_429_TOO_MANY_REQUESTS,
    ErrorCode.INTERNAL_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ErrorCode.UNSUPPORTED_FILE_TYPE: status.HTTP_400_BAD_REQUEST,
    ErrorCode.FILE_TOO_LARGE: status.HTTP_413_CONTENT_TOO_LARGE,
    ErrorCode.CONTRACT_EDIT_CONFLICT: status.HTTP_409_CONFLICT,
}


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, debug=settings.app_debug)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)

    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request.state.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @app.exception_handler(APIException)
    async def handle_api_exception(request: Request, exc: APIException):
        payload = ErrorResponse(
            code=int(exc.code),
            message=exc.message,
            meta=ErrorMeta(
                request_id=request.state.request_id,
                retryable=exc.retryable,
            ),
        )
        return JSONResponse(
            status_code=HTTP_CODE_MAP.get(exc.code, status.HTTP_500_INTERNAL_SERVER_ERROR),
            content=payload.model_dump(),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(request: Request, _exc: Exception):
        payload = ErrorResponse(
            code=int(ErrorCode.INTERNAL_ERROR),
            message="internal error",
            meta=ErrorMeta(
                request_id=request.state.request_id,
                retryable=True,
            ),
        )
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=payload.model_dump())

    return app


app = create_app()
