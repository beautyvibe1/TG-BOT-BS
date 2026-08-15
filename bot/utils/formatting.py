"""Форматирование сообщений бота."""

from __future__ import annotations

import html
from typing import Any

from bot.services.catalog import get_category_by_id, get_meta

CATEGORY_EMOJI = {"care": "🧴", "spf": "☀️", "makeup": "💄"}


def esc(text: str | None) -> str:
    """HTML-экранирование для parse_mode=HTML."""
    return html.escape(text or "")


def format_price(amount: int) -> str:
    return f"{amount:,}".replace(",", " ") + " ₽"


def product_card(product: dict[str, Any]) -> str:
    """HTML-карточка товара."""
    name = product.get("ruName") or product["name"]
    brand = product.get("brand", "")
    category = get_category_by_id(product.get("category", ""))
    cat_label = category["name"] if category else ""
    badge = product.get("badge")
    benefits = product.get("benefits", [])

    lines = [
        f"{'🆕' if badge else '🛍'} <b>{esc(name)}</b>",
        f"<i>{esc(product['name'])}</i>",
        "",
        f"<b>{esc(brand)}</b>{' · ' + esc(product.get('line', '')) if product.get('line') else ''}",
        f"📁 Категория: {esc(cat_label)}",
        f"💰 Цена: <b>{format_price(product['price'])}</b>",
        f"📏 Объём: {esc(product.get('volume', ''))}",
    ]
    if badge:
        lines.append(f"🏷 {esc(badge)}")
    lines += [
        "",
        f"{esc(product.get('summary', ''))}",
    ]
    if benefits:
        lines.append("")
        lines.append("✨ Преимущества:")
        for benefit in benefits[:5]:
            lines.append(f"   • {esc(benefit)}")
    lines += ["", f"✅ {esc(product.get('in_stock', 'В наличии'))}"]
    return "\n".join(lines)


def about_text() -> str:
    meta = get_meta()
    return (
        f"<b>BEAUTY SUPPLY</b> · <i>{meta['tagline']}</i>\n\n"
        f"{esc(meta['description'])}\n\n"
        f"⭐ <b>5.0</b> рейтинг на Avito\n"
        f"🏆 <b>14+</b> лет на рынке (с 2011)\n"
        f"💬 <b>120+</b> отзывов на площадках\n\n"
        f"Проверяем оригинальность каждого товара: маркировка, batch-код, "
        f"фото конкретного экземпляра перед отправкой."
    )


def delivery_text() -> str:
    delivery = __import__("bot.services.catalog", fromlist=["get_delivery"]).get_delivery()
    return (
        "🚚 <b>Доставка</b>\n\n"
        f"{esc(delivery.get('moscow', ''))}\n"
        f"{esc(delivery.get('regions', ''))}\n\n"
        f"⏱ {esc(delivery.get('timing', ''))}\n\n"
        f"✈️ {esc(delivery.get('preorder', ''))}\n\n"
        f"📍 Города: {esc(delivery.get('cities', ''))}\n\n"
        "💳 <b>Оплата:</b> карта РФ (ЮKassa), СБП, перевод менеджеру или "
        "безопасная сделка на Авито."
    )
