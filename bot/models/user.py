"""Модель пользователя Telegram."""

from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, BigIntegerPkMixin, TimestampMixin


class User(BigIntegerPkMixin, TimestampMixin, Base):
    """Пользователь бота."""

    __tablename__ = "users"

    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(128), nullable=True)

    language_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_subscribed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Последний источник перехода (UTM): avito / site / channel / bot
    last_source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_payload: Mapped[str | None] = mapped_column(String(256), nullable=True)

    # Адрес доставки по умолчанию
    default_address: Mapped[str | None] = mapped_column(String(512), nullable=True)
    default_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)

    orders = relationship("Order", back_populates="user", lazy="selectin")

    @property
    def full_name(self) -> str:
        return (self.first_name or "") + (" " + self.last_name if self.last_name else "")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User id={self.id} tg_id={self.tg_id}>"
