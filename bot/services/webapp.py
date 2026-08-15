"""Безопасность Telegram Mini App: валидация initData и обработка sendData."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from urllib.parse import parse_qsl

from bot.config import get_settings

logger = logging.getLogger(__name__)


def _sort_params(pairs: list[tuple[str, str]]) -> str:
    """Собирает строку data-check-string по правилам Telegram."""
    return "\n".join(f"{k}={v}" for k, v in sorted(pairs) if k != "hash")


def validate_init_data(init_data: str, *, auth_date_max_age: int = 86400) -> dict | None:
    """Проверяет подпись initData с помощью секретного ключа бота.

    Возвращает распарсованный словарь при успехе, иначе None.
    """
    if not init_data:
        return None
    settings = get_settings()
    pairs = parse_qsl(init_data, keep_blank_values=True)
    received_hash = dict(pairs).get("hash", "")
    if not received_hash:
        return None

    secret_key = hmac.new(
        b"WebAppData", settings.effective_webapp_secret.encode(), hashlib.sha256
    ).digest()

    data_check_string = _sort_params(pairs)
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(received_hash, calculated_hash):
        logger.warning("initData подпись не совпадает")
        return None

    result = {k: v for k, v in pairs}
    try:
        if "user" in result:
            result["user"] = json.loads(result["user"])
    except (ValueError, TypeError):
        result["user"] = None

    # Проверка свежести auth_date
    import time

    auth_date = result.get("auth_date")
    if auth_date:
        try:
            if int(time.time()) - int(auth_date) > auth_date_max_age:
                logger.warning("initData устарел (auth_date=%s)", auth_date)
                return None
        except ValueError:
            return None

    return result


async def process_webapp_order(bot, message, data: str) -> None:
    """Обрабатывает заказ, присланный из Mini App через sendData()."""
    import json as _json

    from aiogram.utils.keyboard import InlineKeyboardBuilder

    from bot.keyboards.factories import AdminCallback
    from bot.services.catalog import get_or_create_user
    from bot.services.notification import notify_admins

    try:
        payload = _json.loads(data)
    except _json.JSONDecodeError:
        logger.warning("Некорректный JSON из Mini App")
        await message.answer("Не удалось прочитать данные заказа. Попробуйте ещё раз.")
        return

    # Валидация initData (безопасность!)
    init_data = payload.get("initData", "")
    parsed = validate_init_data(init_data) if init_data else None
    if init_data and parsed is None:
        logger.warning("Отклонён заказ из Mini App: неверная подпись initData")
        await message.answer("⚠️ Не удалось проверить безопасность сессии. Заказ не принят.")
        return

    from bot.database import get_sessionmaker

    async with get_sessionmaker()() as db_session:
        user = await get_or_create_user(
            db_session, message.from_user.id, username=message.from_user.username,
            first_name=message.from_user.first_name, last_name=message.from_user.last_name,
        )
        items = payload.get("items", [])
        if not items:
            await message.answer("Корзина пуста.")
            return

        total = 0
        for item in items:
            total += int(item.get("price", 0)) * int(item.get("qty", 1))

        order_number = f"WB-{message.message_id}"
        kb = InlineKeyboardBuilder()
        kb.button(text="📋 Обработать", callback_data=AdminCallback(action="orders").pack())

        order_text = f"🛍 <b>Заказ из Mini App</b>\n\n№ {order_number}\n\n"
        for item in items:
            order_text += f"• {item.get('name', '')} ×{item.get('qty', 1)} — {item.get('price', 0) * item.get('qty', 1)} ₽\n"
        total_fmt = f"{total:,}".replace(",", " ")
        order_text += (
            f"\n💎 Итого: <b>{total_fmt} ₽</b>\n"
            f"👤 {payload.get('customer_name', '')}\n"
            f"📞 {payload.get('phone', '')}\n"
            f"📍 {payload.get('address', '')}\n"
            f"🚚 Доставка: {payload.get('delivery_method', '')}"
        )

        await notify_admins(bot, order_text, kb.as_markup())
        user.last_source = "webapp"
        await db_session.commit()

    total_fmt2 = f"{total:,}".replace(",", " ")
    await message.answer(
        "✅ <b>Заказ из витрины получен!</b>\n\n"
        f"Сумма: <b>{total_fmt2} ₽</b>\n"
        "Менеджер подтвердит заказ и свяжется с вами для оплаты и доставки.\n\n"
        "Статус — в разделе «📦 Мои заказы».",
        parse_mode="HTML",
    )
