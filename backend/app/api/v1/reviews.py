"""Review API endpoints — report, status queries, and WS ticket."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.exceptions import APIException
from app.schemas.api import (
    APIResponse,
    ReviewContradiction,
    ReviewLLMMetaPayload,
    ReviewMissingClause,
    ReviewRAGMetaPayload,
    ReviewReportPayload,
    ReviewRiskItem,
    ReviewStatusPayload,
    ReviewSummaryPayload,
    WSTicketPayload,
)
from app.schemas.errors import ErrorCode
from app.services.review import get_review_tenant_scoped

router = APIRouter()


@router.post(
    "/ws/ticket",
    response_model=APIResponse[WSTicketPayload],
)
async def request_ws_ticket(
    review_id: uuid.UUID = Query(..., description="Review ID to subscribe to"),
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> APIResponse[WSTicketPayload]:
    """Issue a one-time WebSocket ticket for real-time review progress.

    Phase 4: Ticket binds user_id + review_id, expires in 60s, single use.
    Must be defined BEFORE /{review_id} to avoid path shadowing.
    """
    from app.api.v1.ws import issue_ws_ticket

    review = await get_review_tenant_scoped(session, review_id, current_user.tenant_id)
    if not review:
        raise APIException(ErrorCode.REVIEW_NOT_FOUND, "review not found", False)

    ticket, expires_in = issue_ws_ticket(
        user_id=current_user.id,
        review_id=review_id,
        task_id=str(review_id),
    )

    return APIResponse(
        data=WSTicketPayload(
            ticket=ticket,
            expires_in=expires_in,
            review_id=review_id,
        ),
    )


@router.get(
    "/{review_id}",
    response_model=APIResponse[ReviewReportPayload],
)
async def get_review_report(
    review_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> APIResponse[ReviewReportPayload]:
    """Get full review report with risks, contradictions, missing clauses."""
    review = await get_review_tenant_scoped(session, review_id, current_user.tenant_id)
    if not review:
        raise APIException(ErrorCode.REVIEW_NOT_FOUND, "review not found", False)

    report = review.report_json or {}
    payload = ReviewReportPayload(
        id=review.id,
        contract_id=review.contract_id,
        contract_title=review.contract.title if review.contract else None,
        status=review.status,
        progress=review.progress,
        current_stage=review.current_stage,
        schema_version=review.schema_version,
        reviewed_draft=review.reviewed_draft,
        summary=ReviewSummaryPayload(**report["summary"]) if report.get("summary") else None,
        risks=[ReviewRiskItem(**r) for r in report.get("risks", [])],
        contradictions=[ReviewContradiction(**c) for c in report.get("contradictions", [])],
        missing_clauses=[ReviewMissingClause(**m) for m in report.get("missing_clauses", [])],
        llm_meta=ReviewLLMMetaPayload(**report["llm_meta"]) if report.get("llm_meta") else None,
        rag_meta=ReviewRAGMetaPayload(**report["rag_meta"]) if report.get("rag_meta") else None,
        disclaimer=report.get("disclaimer"),
        error_detail=review.error_detail,
        started_at=review.started_at,
        completed_at=review.completed_at,
        created_at=review.created_at,
    )
    return APIResponse(data=payload)


@router.get(
    "/{review_id}/status",
    response_model=APIResponse[ReviewStatusPayload],
)
async def get_review_status(
    review_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> APIResponse[ReviewStatusPayload]:
    """Poll review progress (lightweight, no report body)."""
    review = await get_review_tenant_scoped(session, review_id, current_user.tenant_id)
    if not review:
        raise APIException(ErrorCode.REVIEW_NOT_FOUND, "review not found", False)

    return APIResponse(
        data=ReviewStatusPayload(
            id=review.id,
            contract_id=review.contract_id,
            status=review.status,
            progress=review.progress,
            current_stage=review.current_stage,
            error_detail=review.error_detail,
            started_at=review.started_at,
            completed_at=review.completed_at,
        )
    )
