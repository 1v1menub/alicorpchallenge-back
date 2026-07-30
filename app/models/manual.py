import uuid
from datetime import datetime

from sqlalchemy import Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Manual(Base):
    """A brand manual — the RAG "source of truth" for a product (Module I).

    The whole manual is NOT embedded here; retrieval happens over ManualChunk
    rows (one per section). This row keeps the raw brief, the structured manual,
    and a flattened text rendering for display and the Module III audit.
    """

    __tablename__ = "manuals"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    # freeform brief the Creador wrote
    brief: Mapped[str] = mapped_column(Text)

    # AI-generated hybrid manual (anchors + sections); see StructuredManual
    manual: Mapped[dict] = mapped_column(JSONB)
    # human/vision-readable flattening: UI display + Module III audit context
    raw_text: Mapped[str] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
