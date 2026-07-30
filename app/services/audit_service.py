from uuid import UUID

from langfuse import observe
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.core.tracing import langfuse
from app.models import Manual, ProductAd
from app.models.enums import AdStatus, AdType
from app.schemas.ad import AuditResponse
from app.services import storage, vision


@observe(name="audit-image", capture_input=False, capture_output=False)
async def audit_image(
    session: AsyncSession,
    ad_id: UUID,
    image_bytes: bytes,
    mime_type: str,
) -> AuditResponse | None:
    """Module III (advisory) — check an image vs the manual; store verdict + image.

    Does NOT change status: the human decides via decide_image. The uploaded image
    is kept in Supabase Storage as the current candidate. None if the ad is missing.
    """
    langfuse.update_current_span(input={"ad_id": str(ad_id), "mime_type": mime_type})
    ad = await session.get(ProductAd, ad_id)
    if ad is None:
        langfuse.update_current_span(output="ad not found", level="WARNING")
        return None
    if ad.ad_type != AdType.image_prompt:
        raise ValueError("Audit only applies to ads of type 'image_prompt'")
    if ad.status != AdStatus.pending:
        raise ConflictError(
            f"Ad is already {ad.status.value}; it cannot be re-audited"
        )

    manual = await session.get(Manual, ad.manual_id)
    verdict = await vision.audit_image(manual.raw_text, image_bytes, mime_type)

    # Store the new candidate image, then drop the previous one (if any).
    new_url = await storage.upload_image(image_bytes, mime_type)
    if ad.image_url:
        await storage.delete_image(ad.image_url)
    ad.image_url = new_url
    ad.audit_passed = verdict.passed
    ad.audit_feedback = verdict.feedback
    await session.commit()
    langfuse.update_current_span(output=verdict.model_dump())
    return verdict


async def decide_image(
    session: AsyncSession, ad_id: UUID, new_status: AdStatus
) -> ProductAd | None:
    """Module III — Aprobador B's final approve/reject for image ads.

    Requires a previously audited image. Approve keeps the image; reject deletes it.
    Terminal status is locked. None if the ad is missing.
    """
    ad = await session.get(ProductAd, ad_id)
    if ad is None:
        return None
    if ad.ad_type != AdType.image_prompt:
        raise ConflictError("This endpoint only decides image_prompt ads")
    if ad.status != AdStatus.pending:
        raise ConflictError(
            f"Ad is already {ad.status.value}; its status cannot be changed"
        )
    if not ad.image_url:
        raise ConflictError("No audited image to decide on; audit an image first")

    ad.status = new_status
    if new_status == AdStatus.rejected:
        await storage.delete_image(ad.image_url)
        ad.image_url = None

    await session.commit()
    await session.refresh(ad)
    return ad


async def decide_non_image(
    session: AsyncSession, ad_id: UUID, new_status: AdStatus
) -> ProductAd | None:
    """Module III — Aprobador A's approve/reject for NON-image ads. None if missing.

    A terminal status (approved/rejected) is locked: it cannot be re-set or flipped.
    """
    ad = await session.get(ProductAd, ad_id)
    if ad is None:
        return None
    if ad.ad_type == AdType.image_prompt:
        raise ConflictError("Image ads are decided via the image endpoint")
    if ad.status != AdStatus.pending:
        raise ConflictError(
            f"Ad is already {ad.status.value}; its status cannot be changed"
        )

    ad.status = new_status
    await session.commit()
    await session.refresh(ad)
    return ad
