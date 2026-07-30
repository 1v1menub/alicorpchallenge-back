from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    # Resolve the pgvector `vector` type whether the extension lives in `public`
    # (local docker) or `extensions` (Supabase's default). Non-existent schemas in
    # the search_path are silently ignored, so this is safe in both environments.
    connect_args={"server_settings": {"search_path": "public, extensions"}},
)

AsyncSessionLocal = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a database session per request."""
    async with AsyncSessionLocal() as session:
        yield session
