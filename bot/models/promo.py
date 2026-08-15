"""Модели промокодов и уведомлений."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, BigIntegerPkMixin, TimestampMixin, utcnow


class PromoType(str, enum.Enum):
    PERCENT = "percent"
    FIXED = "fixed"


class Promo(BigIntegerPkMixin, TimestampMixin, Base):
    """Промокод со скидкой."""

    __tablename__ = "promos"

    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    promo_type: Mapped[str] = mapped_column(String(16), default=PromoType.PERCENT.value, nullable=False)
    value: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # % или рубли

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)   # 0/None = безлимит
    used_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    min_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def is_valid(self) -> bool:
        if not self.is_active:
            return False
        if self.max_uses is not None and self.used_count >= self.max_uses:
            return False
        now = utcnow()
        if self.starts_at and now < self.starts_at:
            return False
        if self.expires_at and now > self.expires_at:
            return False
        return True

    def discount_for(self, amount: int) -> int:
        """Скидка в рублях для заданной суммы."""
        if self.promo_type == PromoType.PERCENT.value:
            return round(amount * self.value / 100)
        return min(self.value, amount)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Promo {self.code} {self.promo_type}={self.value}>"


class Consultation(BigIntegerPkMixin, TimestampMixin, Base):
    """Обращение в консультацию (тикет)."""

    __tablename__ = "consultations"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic: Mapped[str | None] = mapped_column(String(256), nullable=True)
    message: Mapped[str] = mapped_column(String(4096), nullable=False)
    answered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    answer_text: Mapped[str | None] = mapped_column(String(4096), nullable=True)
