"""Модели корзины."""

from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, BigIntegerPkMixin, TimestampMixin


class Cart(BigIntegerPkMixin, TimestampMixin, Base):
    """Корзина пользователя (один на пользователя)."""

    __tablename__ = "carts"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )

    items = relationship(
        "CartItem", back_populates="cart", cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def total_items(self) -> int:
        return sum(item.quantity for item in self.items)

    @property
    def total_price(self) -> int:
        return sum(item.quantity * item.product.price for item in self.items)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Cart user={self.user_id} items={self.total_items}>"


class CartItem(BigIntegerPkMixin, TimestampMixin, Base):
    """Позиция корзины."""

    __tablename__ = "cart_items"
    __table_args__ = (UniqueConstraint("cart_id", "product_id", name="uq_cart_product"),)

    cart_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("carts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    cart = relationship("Cart", back_populates="items")
    product = relationship("Product", lazy="joined")

    @property
    def line_total(self) -> int:
        return self.product.price * self.quantity

    def __repr__(self) -> str:  # pragma: no cover
        return f"<CartItem product={self.product_id} qty={self.quantity}>"
