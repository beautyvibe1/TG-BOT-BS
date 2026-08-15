"""Настройка async-движка и фабрики сессий SQLAlchemy."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from bot.config import get_settings
from bot.models import Base


def create_engine() -> AsyncEngine:
    """Создаёт async-движок под текущую DATABASE_URL."""
    url = get_settings().database_url
    kwargs: dict = {"echo": False, "pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"timeout": 30}
    return create_async_engine(url, **kwargs)


# Движок и фабрика сессий создаются лениво при первом обращении.
_engine: AsyncEngine | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_engine()
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    """Создаёт таблицы при первом запуске (development helper).

    Для продакшена используйте Alembic-миграции.
    """
    from bot.config import DATA_DIR

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Аккуратно закрывает пул соединений."""
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI/aiogram-совместимая зависимость сессии."""
    maker = get_sessionmaker()
    async with maker() as session:
        yield session
