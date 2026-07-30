from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, require_module
from app.core.modules import ModuleKey
from app.db.session import get_session
from app.schemas.manual import ManualCreateRequest, ManualListItem, ManualResponse
from app.services.manual_service import create_manual, get_manual, list_manuals

router = APIRouter(prefix="/manuals", tags=["manuals"])


@router.post("", response_model=ManualResponse, status_code=status.HTTP_201_CREATED)
async def create_manual_endpoint(
    payload: ManualCreateRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    _user: Annotated[object, Depends(require_module(ModuleKey.brand_dna))],
) -> ManualResponse:
    """Module I — generate a brand manual from a freeform brief and store it (RAG)."""
    try:
        manual = await create_manual(session, payload.brief)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Manual generation failed: {exc}",
        )
    return ManualResponse.model_validate(manual)


@router.get("", response_model=list[ManualListItem])
async def list_manuals_endpoint(
    session: Annotated[AsyncSession, Depends(get_session)],
    _user: CurrentUser,
) -> list[ManualListItem]:
    """List all brand manuals (any authenticated user)."""
    manuals = await list_manuals(session)
    return [
        ManualListItem(
            id=m.id,
            brand_name=m.manual.get("brand_name", ""),
            brief=m.brief,
            section_count=_section_count(m.manual),
            created_at=m.created_at,
        )
        for m in manuals
    ]


def _section_count(manual: dict) -> int:
    """Number of content blocks: flexible sections + present required anchors."""
    count = len(manual.get("sections") or [])
    if manual.get("summary"):
        count += 1
    if manual.get("color_palette"):
        count += 1
    if manual.get("forbidden_words"):
        count += 1
    return count


@router.get("/{manual_id}", response_model=ManualResponse)
async def get_manual_endpoint(
    manual_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _user: CurrentUser,
) -> ManualResponse:
    """Get a single brand manual (any authenticated user)."""
    manual = await get_manual(session, manual_id)
    if manual is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Manual not found"
        )
    return ManualResponse.model_validate(manual)
