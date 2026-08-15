"""Модель товара."""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class Product(TimestampMixin, Base):
    """Товар каталога."""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    external_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    brand: Mapped[str] = mapped_column(String(128), nullable=False)
    line: Mapped[str | None] = mapped_column(String(128), nullable=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    ru_name: Mapped[str | None] = mapped_column(String(256), nullable=True)

    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True
    )
    price: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    old_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    volume: Mapped[str | None] = mapped_column(String(32), nullable=True)
    badge: Mapped[str | None] = mapped_column(String(64), nullable=True)

    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    benefits: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON-список

    image_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    in_stock: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Кэшируемая цена для сортировки
    price_numeric: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)

    category = relationship("Category", back_populates="products", lazy="joined")

    @property
    def benefits_list(self) -> list[str]:
        import json

        if not self.benefits:
            return []
        try:
            data = json.loads(self.benefits)
            return data if isinstance(data, list) else []
        except (ValueError, TypeError):
            return []

    @property
    def display_name(self) -> str:
        """Локализованное имя: русское или оригинальное."""
        return self.ru_name or self.name

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Product {self.slug}: {self.display_name}>"
