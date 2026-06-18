from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field


T = TypeVar("T")


class ResponseMeta(BaseModel):
    page: int | None = None
    page_size: int | None = None
    total: int | None = None


class APIResponse(BaseModel, Generic[T]):
    code: int = 0
    message: str = "success"
    data: T | None = None
    meta: ResponseMeta | None = None


class ErrorMeta(BaseModel):
    request_id: str
    retryable: bool


class ErrorResponse(BaseModel):
    code: int
    message: str
    data: None = None
    meta: ErrorMeta


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str | None = Field(default=None, max_length=100)
    tenant_name: str = Field(min_length=1, max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserPayload(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    email: EmailStr
    name: str | None
    role: str
    created_at: datetime


class AuthTokenPayload(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserPayload


class ContractPayload(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str | None
    file_url: str
    file_type: str
    file_size: int | None
    contract_type: str | None
    status: str
    created_at: datetime
    updated_at: datetime | None


class ContractDetailPayload(ContractPayload):
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    page_count: int | None


class PaginatedContractsPayload(BaseModel):
    items: list[ContractPayload]


class HealthPayload(BaseModel):
    status: str
    version: str
    checks: dict[str, str]


class ErrorContext(BaseModel):
    request_id: str
    retryable: bool
    details: dict[str, Any] | None = None
