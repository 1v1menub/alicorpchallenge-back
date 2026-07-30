from sqlalchemy import select, text

from app.core.config import settings
from app.core.modules import (
    MODULE_LABELS,
    ROLE_MODULES,
    SEED_USERNAMES,
    ModuleKey,
)
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal, engine
from app.models import Base, Module, Role, User


async def init_db() -> None:
    """Enable pgvector, create tables, and seed roles/modules/users (idempotent)."""
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    await _seed()


async def _seed() -> None:
    async with AsyncSessionLocal() as session:
        # --- modules ---
        existing_modules = (await session.execute(select(Module))).scalars().all()
        modules_by_key = {m.key: m for m in existing_modules}
        for key in ModuleKey:
            if key.value not in modules_by_key:
                module = Module(key=key.value, name=MODULE_LABELS[key])
                session.add(module)
                modules_by_key[key.value] = module
        await session.flush()

        # --- roles (with their module mapping) ---
        existing_roles = (await session.execute(select(Role))).scalars().all()
        roles_by_name = {r.name: r for r in existing_roles}
        for role_name, module_keys in ROLE_MODULES.items():
            if role_name.value not in roles_by_name:
                role = Role(
                    name=role_name.value,
                    modules=[modules_by_key[k.value] for k in module_keys],
                )
                session.add(role)
                roles_by_name[role_name.value] = role
        await session.flush()

        # --- users (one per role) ---
        existing_usernames = {
            u.username for u in (await session.execute(select(User))).scalars().all()
        }
        for role_name, username in SEED_USERNAMES.items():
            if username not in existing_usernames:
                session.add(
                    User(
                        username=username,
                        hashed_password=hash_password(settings.seed_password),
                        role_id=roles_by_name[role_name.value].id,
                    )
                )

        await session.commit()


if __name__ == "__main__":
    import asyncio

    asyncio.run(init_db())
