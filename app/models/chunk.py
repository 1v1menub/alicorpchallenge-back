import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

# gemini-embedding-001 output truncated to 768 dims.
EMBEDDING_DIM = 768


class ManualChunk(Base):
    """A retrievable slice of a brand manual (one per section) — the RAG index."""

    __tablename__ = "manual_chunks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    manual_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("manuals.id", ondelete="CASCADE")
    )

    label: Mapped[str] = mapped_column(String(255))  # section title / chunk label
    content: Mapped[str] = mapped_column(Text)  # the exact text that was embedded
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM))

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
