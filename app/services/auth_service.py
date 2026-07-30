from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import create_access_token, verify_password
from app.models import Role, User


async def authenticate(
    session: AsyncSession, username: str, password: str
) -> User | None:
    """Return the user if credentials are valid, else None. Eager-loads role+modules."""
    result = await session.execute(
        select(User)
        .where(User.username == username)
        .options(selectinload(User.role).selectinload(Role.modules))
    )
    user = result.scalar_one_or_none()
    if user is None or not verify_password(password, user.hashed_password):
        return None
    return user


def issue_token(user: User) -> str:
    """Build a JWT embedding the user's role and its allowed module keys."""
    modules = [m.key for m in user.role.modules]
    return create_access_token(
        subject=user.username,
        uid=str(user.id),
        role=user.role.name,
        modules=modules,
    )
