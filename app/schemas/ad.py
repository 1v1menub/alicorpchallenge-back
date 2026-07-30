from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from app.models.enums import AdStatus, AdType

# ---------------------------------------------------------------------------
# Request / response bodies (Modules II & III)
# ---------------------------------------------------------------------------


class AdCreateRequest(BaseModel):
    manual_id: UUID
    ad_type: AdType
    brief: str | None = None  # what the ad is about; falls back to a per-type default


class AdResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    manual_id: UUID
    ad_type: AdType
    content: str
    status: AdStatus
    audit_passed: bool | None
    audit_feedback: str | None
    image_url: str | None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def _hide_unapproved_image(self) -> "AdResponse":
        # The uploaded image is only surfaced once the ad is approved; while
        # pending we assume no valid image has been accepted yet.
        if self.status != AdStatus.approved:
            self.image_url = None
        return self


class AuditResponse(BaseModel):
    """Result of the multimodal image audit (Module III)."""

    passed: bool
    feedback: str


class StatusUpdateRequest(BaseModel):
    """Human approve/reject decision. Only approved or rejected are valid here."""

    status: AdStatus
