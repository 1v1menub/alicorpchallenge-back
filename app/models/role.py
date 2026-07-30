from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.associations import role_modules
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.module import Module
    from app.models.user import User


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(50), unique=True)

    modules: Mapped[list[Module]] = relationship(
        secondary=role_modules, back_populates="roles"
    )
    users: Mapped[list[User]] = relationship(back_populates="role")
