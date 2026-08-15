"""Логика корзины: расчёты, промокоды, рендер сообщений."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models import Cart, CartItem, Promo, User


def format_price(amount: int) -> str:
    """Форматирует цену: 11599 -> «11 599 ₽»."""
    return f"{amount:,}".replace(",", " ") + " ₽"


async def get_promo(db: AsyncSession, code: str) -> Promo | None:
    return await db.scalar(select(Promo).where(Promo.code == code.strip().upper()))


async def apply_promo(db: AsyncSession, cart: Cart, code: str) -> tuple[int, str, Promo | None]:
    """Применяет промокод к корзине.

    Возвращает (discount, message, promo). Сообщение может быть об ошибке.
    """
    promo = await get_promo(db, code)
    if promo is None:
        return 0, "❌ Промокод не найден. Проверьте написание.", None
    if not promo.is_valid:
        return 0, "❌ Промокод неактивен или срок его действия истёк.", None
    if cart.total_price < promo.min_order:
        return (
            0,
            f"❌ Промокод действует от {format_price(promo.min_order)}.",
            promo,
        )
    discount = promo.discount_for(cart.total_price)
    return discount, f"✅ Промокод {promo.code} применён: −{format_price(discount)}", promo


def render_cart(cart: Cart, *, discount: int = 0, delivery_cost: int = 0) -> str:
    """Текстовое представление корзины."""
    if not cart.items:
        return "🛒 *Корзина пуста.*\n\nЗагляните в каталог — там ждёт ваша идеальная уходовая рутина ✨"
    lines = ["🛒 *Ваша корзина:*", ""]
    for idx, item in enumerate(cart.items, start=1):
        name = item.product.ru_name or item.product.name
        lines.append(
            f"{idx}. {name}\n"
            f"   {item.product.brand} · {format_price(item.product.price)}\n"
            f"   ×{item.quantity} = *{format_price(item.line_total)}*"
        )
    lines.append("")
    lines.append(f"Сумма: *{format_price(cart.total_price)}*")
    if discount:
        lines.append(f"Скидка: −{format_price(discount)}")
        lines.append(f"Промокод: *{format_price(cart.total_price - discount)}*")
    if delivery_cost:
        lines.append(f"Доставка: {format_price(delivery_cost)}")
    if discount or delivery_cost:
        lines.append(f"💎 Итого: *{format_price(cart.total_price - discount + delivery_cost)}*")
    return "\n".join(lines)
