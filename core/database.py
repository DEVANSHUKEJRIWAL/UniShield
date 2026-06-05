"""SQLAlchemy async database setup."""

from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from core.config import settings

if settings.uses_sqlite:
    Path(settings.database_uri.split("///")[-1]).parent.mkdir(parents=True, exist_ok=True)

connect_args: dict = {}
if settings.uses_sqlite:
    connect_args = {"check_same_thread": False}

engine = create_async_engine(
    settings.database_uri,
    echo=False,
    pool_pre_ping=not settings.uses_sqlite,
    connect_args=connect_args,
)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions."""
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Create all tables."""
    import core.models  # noqa: F401 — register ORM models on Base.metadata

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def bootstrap_dev_data() -> None:
    """Create tables and seed demo users if database is empty."""
    await init_db()
    if not settings.auto_seed:
        return
    from core.seed import seed_if_empty

    async with SessionLocal() as session:
        seeded = await seed_if_empty(session)
        if seeded:
            print("UniShield: seeded demo users (analyst@meridian.com / analyst123)")
