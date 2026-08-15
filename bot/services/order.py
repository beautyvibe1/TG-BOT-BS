"""Логика заказов: создание, нумерация, рендер, статусы."""

from __future__ import annotations

import secrets
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models import (
    Cart,
    CartItem,
    Order,
    OrderItem,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    User,
)

from .cart import format_price


async def next_order_number(db: AsyncSession) -> str:
    """Генерирует человекочитаемый номер заказа вида BS-240815-ABC12."""
    date_part = datetime.now().strftime("%y%m%d")
    suffix = secrets.token_hex(3).upper()[:5]
    candidate = f"BS-{date_part}-{suffix}"
    while await db.scalar(select(Order).where(Order.number == candidate)) is not None:
        suffix = secrets.token_hex(3).upper()[:5]
        candidate = f"BS-{date_part}-{suffix}"
    return candidate


async def count_orders(db: AsyncSession) -> int:
    return int((await db.scalar(select(func.count(Order.id)))) or 0)


async def create_order_from_cart(
    db: AsyncSession,
    user: User,
    cart: Cart,
    *,
    name: str,
    phone: str,
    address: str,
    delivery_method: str,
    payment_method: str,
    comment: str = "",
    discount: int = 0,
    delivery_cost: int = 0,
    promo_code: str | None = None,
    source: str | None = None,
) -> Order:
    """Превращает корзину в заказ со снимками позиций."""
    from sqlalchemy.orm import selectinload

    # Явно выбираем позиции корзины (избегаем ленивой загрузки relationship)
    cart_items = (
        await db.scalars(
            select(CartItem)
            .where(CartItem.cart_id == cart.id)
            .options(selectinload(CartItem.product))
        )
    ).all()
    items_total = sum(item.product.price * item.quantity for item in cart_items)

    order = Order(
        number=await next_order_number(db),
        user_id=user.id,
        status=OrderStatus.NEW.value,
        delivery_method=delivery_method,
        payment_method=payment_method,
        payment_status=PaymentStatus.PENDING.value,
        customer_name=name,
        phone=phone,
        address=address,
        comment=comment,
        items_total=items_total,
        delivery_cost=delivery_cost,
        discount=discount,
        total=items_total - discount + delivery_cost,
        promo_code=promo_code,
        source=source,
    )
    db.add(order)
    await db.flush()

    # Добавляем позиции напрямую (не трогая relationship-коллекцию,
    # чтобы избежать синхронной lazy-загрузки).
    for item in cart_items:
        p = item.product
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=p.id,
                product_slug=p.slug,
                product_name=p.ru_name or p.name,
                brand=p.brand,
                volume=p.volume,
                image_url=p.image_url,
                unit_price=p.price,
                quantity=item.quantity,
            )
        )
    await db.commit()

    # Перечитываем заказ вместе с позициями (selectin-загрузка).
    created = await db.scalar(
        select(Order).where(Order.id == order.id).options(selectinload(Order.items))
    )
    return created or order


def render_order(order: Order) -> str:
    """Подробное представление заказа (для клиента и админа)."""
    lines = [
        f"📋 *Заказ {order.number}*",
        "",
    ]
    for item in order.items:
        lines.append(f"• {item.product_name} ×{item.quantity} — {format_price(item.line_total)}")
    lines.append("")
    lines.append(f"Товары: {format_price(order.items_total)}")
    if order.discount:
        lines.append(f"Скидка: −{format_price(order.discount)}")
    if order.delivery_cost:
        lines.append(f"Доставка: {format_price(order.delivery_cost)}")
    lines.append(f"💎 *Итого: {format_price(order.total)}*")
    lines.append("")
    lines.append(f"👤 {order.customer_name}")
    lines.append(f"📞 {order.phone or '—'}")
    lines.append(f"📍 {order.address or '—'}")
    if order.comment:
        lines.append(f"💬 {order.comment}")
    lines.append("")
    lines.append(f"🚚 Доставка: {order.delivery_method or '—'}")
    lines.append(f"💳 Оплата: {order.payment_method or '—'}")
    lines.append(f"Статус: *{order.status_enum.label}*")
    return "\n".join(lines)


DELIVERY_METHOD_LABELS = {
    "moscow_courier": "Курьер по Москве",
    "cdek": "СДЭК",
    "avito_delivery": "Avito Доставка",
    "self_pickup": "Самовывоз",
}

PAYMENT_METHOD_LABELS = {
    "card": "Карта (ЮKassa)",
    "sbp": "СБП",
    "transfer": "Перевод менеджеру",
    "telegram_stars": "Telegram Stars",
    "avito": "Безопасная сделка на Авито",
}


def method_label(method: str | None) -> str:
    return DELIVERY_METHOD_LABELS.get(method or "", method or "—")


def payment_label(method: str | None) -> str:
    return PAYMENT_METHOD_LABELS.get(method or "", method or "—")
