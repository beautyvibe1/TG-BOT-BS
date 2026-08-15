"""Модели заказа и позиций заказа."""

from __future__ import annotations

import enum

from sqlalchemy import BigInteger, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, BigIntegerPkMixin, TimestampMixin


class OrderStatus(str, enum.Enum):
    """Статусы жизненного цикла заказа."""

    NEW = "new"                  # создан, ожидает оплаты/подтверждения
    CONFIRMED = "confirmed"      # подтверждён менеджером
    PAID = "paid"                # оплачен
    PROCESSING = "processing"    # собирается
    SHIPPED = "shipped"          # передан в доставку
    DELIVERED = "delivered"      # доставлен
    CANCELLED = "cancelled"      # отменён
    REFUNDED = "refunded"        # возврат

    @property
    def label(self) -> str:
        return STATUS_LABELS[self]


STATUS_LABELS: dict[OrderStatus, str] = {
    OrderStatus.NEW: "🆕 Новый",
    OrderStatus.CONFIRMED: "✅ Подтверждён",
    OrderStatus.PAID: "💳 Оплачен",
    OrderStatus.PROCESSING: "📦 Собирается",
    OrderStatus.SHIPPED: "🚚 В пути",
    OrderStatus.DELIVERED: "🎉 Доставлен",
    OrderStatus.CANCELLED: "❌ Отменён",
    OrderStatus.REFUNDED: "↩️ Возврат",
}


class DeliveryMethod(str, enum.Enum):
    MOSCOW_COURIER = "moscow_courier"
    CDEK = "cdek"
    AVITO = "avito_delivery"
    SELF_PICKUP = "self_pickup"


class PaymentMethod(str, enum.Enum):
    CARD = "card"                      # карта РФ / ЮKassa
    SB_P = "sbp"                       # СБП
    TRANSFER = "transfer"              # перевод вручную + подтверждение админа
    TELEGRAM_STARS = "telegram_stars"  # Telegram Stars
    AVITO = "avito"                    # безопасная сделка на Авито


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"


class Order(BigIntegerPkMixin, TimestampMixin, Base):
    """Заказ."""

    __tablename__ = "orders"

    number: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    status: Mapped[str] = mapped_column(String(24), default=OrderStatus.NEW.value, nullable=False, index=True)
    delivery_method: Mapped[str | None] = mapped_column(String(32), nullable=True)
    payment_method: Mapped[str | None] = mapped_column(String(32), nullable=True)
    payment_status: Mapped[str] = mapped_column(
        String(24), default=PaymentStatus.PENDING.value, nullable=False
    )

    # Контактные данные клиента
    customer_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    address: Mapped[str | None] = mapped_column(String(512), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Итоги
    items_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    delivery_cost: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    discount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    promo_code: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Оплата / Telegram
    currency: Mapped[str] = mapped_column(String(8), default="RUB", nullable=False)
    telegram_payment_charge_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    provider_payment_charge_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    invoice_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Источник перехода (UTM)
    source: Mapped[str | None] = mapped_column(String(32), nullable=True)

    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan", lazy="selectin")
    user = relationship("User", back_populates="orders", lazy="joined")

    @property
    def status_enum(self) -> OrderStatus:
        try:
            return OrderStatus(self.status)
        except ValueError:
            return OrderStatus.NEW

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Order {self.number} total={self.total} {self.status}>"


class OrderItem(BigIntegerPkMixin, Base):
    """Снимок позиции на момент заказа (цена зафиксирована)."""

    __tablename__ = "order_items"

    order_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True)

    # Снимок данных товара
    product_slug: Mapped[str] = mapped_column(String(64), nullable=False)
    product_name: Mapped[str] = mapped_column(String(256), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(128), nullable=True)
    volume: Mapped[str | None] = mapped_column(String(32), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    unit_price: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    order = relationship("Order", back_populates="items")

    @property
    def line_total(self) -> int:
        return self.unit_price * self.quantity

    def __repr__(self) -> str:  # pragma: no cover
        return f"<OrderItem {self.product_slug} x{self.quantity}>"
