from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Hybrid brand manual: a few stable "anchor" fields that downstream modules and
# the UI depend on, plus a flexible list of product-specific sections. Each
# section becomes a RAG chunk (see manual_service). Stored as JSONB.
# ---------------------------------------------------------------------------


class ColorSpec(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str
    hex: str
    usage: str | None = None  # e.g. "primary background", "accent only"


class Section(BaseModel):
    """A free-form, product-specific section of the manual (one RAG chunk)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str
    content: str


class StructuredManual(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    # --- anchors: guaranteed, injected directly by Modules II/III ---
    brand_name: str
    summary: str
    forbidden_words: list[str] = Field(default_factory=list)
    color_palette: list[ColorSpec] = Field(default_factory=list)

    # --- flexible sections: adapted to the product, embedded as chunks ---
    sections: list[Section] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Request / response bodies (Module I)
# ---------------------------------------------------------------------------


class ManualCreateRequest(BaseModel):
    """Freeform brief the Creador writes; the AI generates the manual from it."""

    brief: str


class ManualResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    brief: str
    manual: StructuredManual
    created_at: datetime


class ManualListItem(BaseModel):
    """Lightweight manual entry for list views."""

    id: UUID
    brand_name: str
    brief: str
    section_count: int  # flexible sections + required anchors (summary/palette/forbidden)
    created_at: datetime
