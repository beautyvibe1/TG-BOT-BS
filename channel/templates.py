"""Шаблоны постов для канала."""

from __future__ import annotations

from typing import Any

from bot.config import get_settings

CATEGORY_EMOJI = {"care": "🧴", "spf": "☀️", "makeup": "💄"}


def _format_price(price: int) -> str:
    return f"{price:,}".replace(",", " ") + " ₽"


def post_product_html(product: dict[str, Any]) -> str:
    """Пост «Новый товар / поступление» (HTML)."""
    settings = get_settings()
    name = product.get("ruName") or product["name"]
    badge = product.get("badge")
    line = product.get("line")
    benefits = product.get("benefits", [])[:3]

    header = "📦 <b>Поступление</b>" if not badge else f"🏷 <b>{badge}</b>"
    lines = [
        header,
        "",
        f"<b>{name}</b>",
        f"<i>{product.get('name', '')}</i>",
        "",
        f"🏷 Бренд: <b>{product.get('brand', '')}</b>",
    ]
    if line:
        lines.append(f"📏 Линия: {line}")
    lines += [
        f"📦 Объём: {product.get('volume', '')}",
        f"💰 <b>{_format_price(product['price'])}</b>",
        "",
    ]
    if product.get("summary"):
        lines.append(product["summary"])
    if benefits:
        lines.append("")
        for benefit in benefits:
            lines.append(f"✨ • {benefit}")
    lines += [
        "",
        f"✅ {product.get('in_stock', 'В наличии')}",
        "",
        "🔻 <b>Оформить заказ</b> — в нашем боте 👇",
    ]
    return "\n".join(lines)


def post_deal_html(product: dict[str, Any], discount_percent: int = 10) -> str:
    """Пост «Акция/скидка» (HTML)."""
    price = product["price"]
    old_price = round(price * 100 / (100 - discount_percent))
    name = product.get("ruName") or product["name"]
    return (
        "🔥 <b>АКЦИЯ!</b>\n\n"
        f"<b>{name}</b>\n"
        f"{product.get('brand', '')}\n\n"
        f"<s>{_format_price(old_price)}</s> → <b>{_format_price(price)}</b>\n"
        f"Выгода −{discount_percent}% 🎉\n\n"
        f"✅ {product.get('in_stock', 'В наличии')}\n\n"
        "🔻 Заказать в боте 👇"
    )


def post_tip_html() -> str:
    """Полезный beauty-совет."""
    return (
        "💡 <b>Beauty-совет</b>\n\n"
        "Витамин C и ретинол — мощная пара, но их нужно чередовать:\n\n"
        "☀️ <b>Утро</b> — витамин C + SPF 30–50\n"
        "🌙 <b>Вечер</b> — ретинол (2–3 раза в неделю на старте)\n\n"
        "Так активы работают без раздражения, а кожа получает максимум пользы ✨\n\n"
        "Подберём уход под вашу кожу — в нашем боте 👇"
    )


def post_top_week_html(top_products: list[dict[str, Any]]) -> str:
    """Подборка «Топ товаров недели»."""
    lines = ["📊 <b>Топ товаров недели</b>", ""]
    medals = ["🥇", "🥈", "🥉"]
    for idx, product in enumerate(top_products[:5]):
        medal = medals[idx] if idx < 3 else f"{idx + 1}."
        name = product.get("ruName") or product["name"]
        lines.append(f"{medal} <b>{name}</b>")
        lines.append(f"   {product.get('brand', '')} · {_format_price(product['price'])}")
    lines += [
        "",
        "Полный каталог — в нашем боте 👇",
    ]
    return "\n".join(lines)


def build_product_keyboard(product: dict[str, Any]):
    """Inline-кнопки поста: «Заказать» (бот) и «На сайте»."""
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    settings = get_settings()
    builder = InlineKeyboardBuilder()
    bot_username = settings.bot_username.lstrip("@")
    deep_link = f"https://t.me/{bot_username}?start=product_{product['slug']}"
    builder.button(text="🛒 Заказать", url=deep_link)
    builder.button(text="🌐 На сайте", url=settings.site_catalog_url)
    builder.adjust(2)
    return builder.as_markup()
