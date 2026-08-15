"""Общие фикстуры для тестов."""

from __future__ import annotations

import os

os.environ["BOT_TOKEN"] = "1234567890:TESTTESTTESTTESTTESTTESTTEST"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["USE_REDIS"] = "false"
os.environ["PAYMENTS_ENABLED"] = "false"

import pytest_asyncio  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from bot.models import Base  # noqa: E402


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def catalog(db_session):
    """Наполняет БД товарами из единого каталога."""
    from bot.services import catalog

    await catalog.seed_database(db_session)
    return catalog
