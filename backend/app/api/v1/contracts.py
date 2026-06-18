import uuid

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.exceptions import APIException
from app.schemas.api import (
    APIResponse,
    ContractDetailPayload,
    ContractPayload,
    PaginatedContractsPayload,
    ResponseMeta,
)
from app.schemas.errors import ErrorCode
from app.services.contract import ContractServiceError, create_contract, get_contract, list_contracts


router = APIRouter()


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
    return APIResponse(
        data=PaginatedContractsPayload(
            items=[ContractPayload.model_validate(item) for item in items]
        ),
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
    return APIResponse(data=ContractDetailPayload.model_validate(contract))
