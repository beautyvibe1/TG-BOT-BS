"""Базовые классы SQLAlchemy-моделей."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import BigInteger, DateTime, Integer, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# BigInteger с автоинкрементом: на SQLite используется INTEGER (rowid-алиас),
# на PostgreSQL — BIGINT.
BigIntPk = BigInteger().with_variant(Integer, "sqlite")


def utcnow() -> datetime:
    """Текущее UTC-время (timezone-aware)."""
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Декларативный базовый класс всех моделей."""


class TimestampMixin:
    """Добавляет created_at / updated_at к модели."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class BigIntegerPkMixin:
    """BigInt первичный ключ (совместим с TG id)."""

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
