from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, require_module
from app.core.exceptions import ConflictError
from app.core.modules import ModuleKey
from app.db.session import get_session
from app.models.enums import AdStatus, AdType
from app.schemas.ad import (
    AdCreateRequest,
    AdResponse,
    AuditResponse,
    StatusUpdateRequest,
)
from app.services.ad_service import create_ad, get_ad, list_ads
from app.services.audit_service import audit_image, decide_image, decide_non_image

router = APIRouter(prefix="/ads", tags=["ads"])


@router.post("", response_model=AdResponse, status_code=status.HTTP_201_CREATED)
async def create_ad_endpoint(
    payload: AdCreateRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    _user: Annotated[object, Depends(require_module(ModuleKey.creative_engine))],
) -> AdResponse:
    """Module II — generate a brand-consistent ad from a manual (status: pending)."""
    try:
        ad = await create_ad(session, payload.manual_id, payload.ad_type, payload.brief)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Ad generation failed: {exc}",
        )
    if ad is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Manual not found"
        )
    return AdResponse.model_validate(ad)


@router.post("/{ad_id}/image", response_model=AuditResponse)
async def audit_image_endpoint(
    ad_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    image: Annotated[UploadFile, File()],
    _user: Annotated[object, Depends(require_module(ModuleKey.image_audit))],
) -> AuditResponse:
    """Module III — audit an image vs the manual (advisory; stores verdict + image)."""
    if not (image.content_type or "").startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be an image",
        )
    try:
        verdict = await audit_image(session, ad_id, await image.read(), image.content_type)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if verdict is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ad not found"
        )
    return verdict


@router.patch("/{ad_id}/image", response_model=AdResponse)
async def decide_image_endpoint(
    ad_id: UUID,
    payload: StatusUpdateRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    _user: Annotated[object, Depends(require_module(ModuleKey.image_audit))],
) -> AdResponse:
    """Module III — Aprobador B's final approve/reject for image ads."""
    if payload.status == AdStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="status must be 'approved' or 'rejected'",
        )
    try:
        ad = await decide_image(session, ad_id, payload.status)
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if ad is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ad not found"
        )
    return AdResponse.model_validate(ad)


@router.patch("/{ad_id}/non_image", response_model=AdResponse)
async def decide_non_image_endpoint(
    ad_id: UUID,
    payload: StatusUpdateRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    _user: Annotated[object, Depends(require_module(ModuleKey.non_image_audit))],
) -> AdResponse:
    """Module III — Aprobador A's approve/reject for non-image ads."""
    if payload.status == AdStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="status must be 'approved' or 'rejected'",
        )
    try:
        ad = await decide_non_image(session, ad_id, payload.status)
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if ad is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ad not found"
        )
    return AdResponse.model_validate(ad)


@router.get("", response_model=list[AdResponse])
async def list_ads_endpoint(
    session: Annotated[AsyncSession, Depends(get_session)],
    _user: CurrentUser,
    manual_id: UUID | None = None,
    ad_type: AdType | None = None,
    status_filter: Annotated[AdStatus | None, Query(alias="status")] = None,
) -> list[AdResponse]:
    """List ads (any authenticated user); optional manual/type/status filters."""
    ads = await list_ads(session, manual_id, ad_type, status_filter)
    return [AdResponse.model_validate(a) for a in ads]


@router.get("/{ad_id}", response_model=AdResponse)
async def get_ad_endpoint(
    ad_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _user: CurrentUser,
) -> AdResponse:
    """Get a single ad (any authenticated user)."""
    ad = await get_ad(session, ad_id)
    if ad is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ad not found"
        )
    return AdResponse.model_validate(ad)
