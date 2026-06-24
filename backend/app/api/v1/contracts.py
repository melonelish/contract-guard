import uuid

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.exceptions import APIException
from app.schemas.api import (
    APIResponse,
    ContractDetailPayload,
    ContractPayload,
    DraftPayload,
    PaginatedContractsPayload,
    ResponseMeta,
    ReviewBriefPayload,
    ReviewPayload,
    ReviewSummaryPayload,
    SaveDraftRequest,
)
from app.schemas.errors import ErrorCode
from app.services.contract import (
    ContractServiceError,
    create_contract,
    get_contract,
    list_contracts,
)
from app.services.queue import enqueue_review_task
from app.services.review import (
    ReviewServiceError,
    create_review,
    get_latest_reviews_for_contracts,
)

router = APIRouter()


def build_review_brief(review) -> ReviewBriefPayload | None:
    if not review:
        return None
    if review.report_json and review.report_json.get("summary"):
        summary = ReviewSummaryPayload(**review.report_json["summary"])
    else:
        summary = None
    return ReviewBriefPayload(
        id=review.id,
        status=review.status,
        progress=review.progress,
        summary=summary,
        error_detail=review.error_detail,
        created_at=review.created_at,
    )


@router.post("/upload", response_model=APIResponse[ContractPayload], status_code=status.HTTP_201_CREATED)
async def upload_contract(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> APIResponse[ContractPayload]:
    try:
        content = await file.read()
        contract = await create_contract(
            session=session,
            user=current_user,
            title=title,
            filename=file.filename or "contract.pdf",
            content=content,
            content_type=file.content_type or "application/octet-stream",
        )
    except ContractServiceError as exc:
        message = str(exc)
        if message == "unsupported file type":
            raise APIException(ErrorCode.UNSUPPORTED_FILE_TYPE, "unsupported file type", False) from exc
        if message == "file too large":
            raise APIException(ErrorCode.FILE_TOO_LARGE, "file too large", False) from exc
        raise APIException(ErrorCode.INTERNAL_ERROR, "internal error", True) from exc

    return APIResponse(data=ContractPayload.model_validate(contract))


@router.get("", response_model=APIResponse[PaginatedContractsPayload])
async def get_contracts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> APIResponse[PaginatedContractsPayload]:
    items, total = await list_contracts(session, current_user, page, page_size)

    # Batch-fetch latest reviews for all contracts in this page
    contract_ids = [item.id for item in items]
    latest_reviews = await get_latest_reviews_for_contracts(session, contract_ids)

    payloads = []
    for item in items:
        payload = ContractPayload.model_validate(item)
        payload.latest_review = build_review_brief(latest_reviews.get(item.id))
        payloads.append(payload)

    return APIResponse(
        data=PaginatedContractsPayload(items=payloads),
        meta=ResponseMeta(page=page, page_size=page_size, total=total),
    )


@router.get("/{contract_id}", response_model=APIResponse[ContractDetailPayload])
async def get_contract_detail(
    contract_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> APIResponse[ContractDetailPayload]:
    contract = await get_contract(session, current_user, contract_id)
    if not contract:
        raise APIException(ErrorCode.NOT_FOUND, "not found", False)
    latest_reviews = await get_latest_reviews_for_contracts(session, [contract.id])
    payload = ContractDetailPayload.model_validate(contract)
    payload.latest_review = build_review_brief(latest_reviews.get(contract.id))
    return APIResponse(data=payload)


@router.post(
    "/{contract_id}/review",
    response_model=APIResponse[ReviewPayload],
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_review(
    contract_id: uuid.UUID,
    use_draft: bool = Query(default=False, description="If true, review the draft content instead of original file"),
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> APIResponse[ReviewPayload]:
    """Trigger a real LLM review via Redis queue. Returns 409 if already running.

    Phase 4: Review task is pushed to Redis Stream instead of BackgroundTasks,
    decoupling execution from the HTTP request lifecycle.

    Phase v12: Support draft review via use_draft query parameter.
    """
    contract = await get_contract(session, current_user, contract_id)
    if not contract:
        raise APIException(ErrorCode.NOT_FOUND, "contract not found", False)

    try:
        review = await create_review(session, current_user, contract, use_draft_content=use_draft)
    except ReviewServiceError as exc:
        raise APIException(ErrorCode(exc.code), exc.message, True) from exc

    # Phase 4: enqueue to Redis Stream (decoupled from request lifecycle)
    # Phase v12: Pass use_draft_content and contract_id to worker
    try:
        await enqueue_review_task(
            review_id=review.id,
            contract_title=contract.title,
            contract_file_url=contract.file_url,
            contract_file_type=contract.file_type,
            use_draft_content=use_draft,
            contract_id=contract.id,
        )
    except Exception as exc:
        # Compensation: mark the just-created review as failed so it
        # does not block future retries with "review already in progress".
        from datetime import datetime

        from app.db.models import Review as ReviewModel

        db_review = await session.get(ReviewModel, review.id)
        if db_review and db_review.status == "queued":
            db_review.status = "failed"
            db_review.error_detail = (
                f"任务入队失败，审查未能启动: {exc}"
            )[:2000]
            db_review.completed_at = datetime.utcnow()
            await session.commit()
        raise APIException(
            ErrorCode.INTERNAL_ERROR,
            f"failed to enqueue review task: {exc}",
            True,
        ) from exc

    return APIResponse(data=ReviewPayload.model_validate(review))


@router.get("/{contract_id}/draft", response_model=APIResponse[DraftPayload])
async def get_contract_draft(
    contract_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> APIResponse[DraftPayload]:
    """Get draft content for a contract."""
    from app.services.draft import get_draft

    try:
        content, updated_at = await get_draft(session, current_user, contract_id)
    except ValueError as exc:
        raise APIException(ErrorCode.NOT_FOUND, str(exc), False) from exc

    return APIResponse(
        data=DraftPayload(
            contract_id=contract_id,
            content=content,
            updated_at=updated_at,
        )
    )


@router.post("/{contract_id}/draft", response_model=APIResponse[DraftPayload])
async def save_contract_draft(
    contract_id: uuid.UUID,
    request: SaveDraftRequest,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> APIResponse[DraftPayload]:
    """Save draft content for a contract."""
    from app.services.draft import save_draft

    try:
        content, updated_at = await save_draft(
            session, current_user, contract_id, request.content
        )
    except ValueError as exc:
        raise APIException(ErrorCode.NOT_FOUND, str(exc), False) from exc

    return APIResponse(
        data=DraftPayload(
            contract_id=contract_id,
            content=content,
            updated_at=updated_at,
        )
    )
