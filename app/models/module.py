from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.associations import role_modules
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.role import Role


class Module(Base):
    __tablename__ = "modules"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(50), unique=True)  # e.g. "brand_dna"
    name: Mapped[str] = mapped_column(String(100))

    roles: Mapped[list[Role]] = relationship(
        secondary=role_modules, back_populates="modules"
    )
