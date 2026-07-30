from app.models.ad import ProductAd
from app.models.associations import role_modules
from app.models.base import Base
from app.models.chunk import ManualChunk
from app.models.manual import Manual
from app.models.module import Module
from app.models.role import Role
from app.models.user import User

# Importing every ORM class here registers it on Base.metadata so that
# schema-creation / migrations see every table and relationship.
__all__ = [
    "Base",
    "Manual",
    "ManualChunk",
    "ProductAd",
    "User",
    "Role",
    "Module",
    "role_modules",
]
