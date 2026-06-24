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
    latest_review: ReviewBriefPayload | None = None


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


# --- Review schemas ---

class ReviewPayload(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    contract_id: uuid.UUID
    status: str
    progress: int
    current_stage: str | None
    schema_version: str
    reviewed_draft: bool = False
    error_detail: str | None = None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class ReviewSummaryPayload(BaseModel):
    total_risks: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0


class ReviewRiskItem(BaseModel):
    clause_id: str
    clause_code: str
    risk_level: str
    risk_category: str
    original_text: str
    legal_analysis: str
    legal_basis: str = "依据不足，基于法理分析"
    basis_excerpt: str = ""
    basis_source: str = ""
    plain_explanation: str
    suggested_revision: str
    confidence: float


class ReviewMissingClause(BaseModel):
    name: str
    reason: str


class ReviewContradiction(BaseModel):
    clause_a: str
    clause_b: str
    conflict_type: str
    description: str


class ReviewLLMMetaPayload(BaseModel):
    provider_model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    finish_reason: str | None = None


class ReviewRAGMetaPayload(BaseModel):
    enabled: bool = False
    hit_count: int = 0
    mode: str = "model_only"
    queries: list[str] = []


class ReviewReportPayload(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    contract_id: uuid.UUID
    contract_title: str | None
    status: str
    progress: int
    current_stage: str | None
    schema_version: str
    reviewed_draft: bool = False
    summary: ReviewSummaryPayload | None = None
    risks: list[ReviewRiskItem] = []
    contradictions: list[ReviewContradiction] = []
    missing_clauses: list[ReviewMissingClause] = []
    llm_meta: ReviewLLMMetaPayload | None = None
    rag_meta: ReviewRAGMetaPayload | None = None
    disclaimer: str | None = None
    error_detail: str | None = None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class ReviewStatusPayload(BaseModel):
    id: uuid.UUID
    contract_id: uuid.UUID
    status: str
    progress: int
    current_stage: str | None
    error_detail: str | None = None
    started_at: datetime | None
    completed_at: datetime | None


class ReviewBriefPayload(BaseModel):
    """Brief review info for embedding in contract list."""
    id: uuid.UUID
    status: str
    progress: int
    summary: ReviewSummaryPayload | None = None
    error_detail: str | None = None
    created_at: datetime


class ErrorContext(BaseModel):
    request_id: str
    retryable: bool
    details: dict[str, Any] | None = None


# --- Phase 4: WebSocket ticket ---

class WSTicketPayload(BaseModel):
    """Response payload for WebSocket ticket issuance."""
    ticket: str
    expires_in: int
    review_id: uuid.UUID


class DraftPayload(BaseModel):
    """Contract draft payload."""
    contract_id: uuid.UUID
    content: str | None
    updated_at: datetime | None


class SaveDraftRequest(BaseModel):
    """Request to save draft content."""
    content: str
