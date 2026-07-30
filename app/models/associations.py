from sqlalchemy import Column, ForeignKey, Table

from app.models.base import Base

# Many-to-many: which modules each role can access.
role_modules = Table(
    "role_modules",
    Base.metadata,
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("module_id", ForeignKey("modules.id", ondelete="CASCADE"), primary_key=True),
)
