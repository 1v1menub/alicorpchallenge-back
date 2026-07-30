import uuid
from datetime import datetime

from sqlalchemy import Enum, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import AdStatus, AdType


class ProductAd(Base):
    """A piece of generated content tied to a brand manual (Modules II & III)."""

    __tablename__ = "product_ads"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    manual_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("manuals.id", ondelete="CASCADE")
    )

    ad_type: Mapped[AdType] = mapped_column(Enum(AdType, name="ad_type"))
    content: Mapped[str] = mapped_column(Text)  # the generated text (Module II)

    status: Mapped[AdStatus] = mapped_column(
        Enum(AdStatus, name="ad_status"), default=AdStatus.pending
    )

    # --- latest multimodal image audit result, set by Aprobador B (Module III) ---
    audit_passed: Mapped[bool | None] = mapped_column(nullable=True)
    audit_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    # public URL of the audited candidate image in Supabase Storage; kept if approved
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    # bumped on every update (status decisions, image audit)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
