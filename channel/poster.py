"""Генератор и публикатор постов в канал."""

from __future__ import annotations

import logging
import random

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from bot.config import get_settings
from bot.services.catalog import get_product_by_slug, get_products

from .templates import (
    build_product_keyboard,
    post_deal_html,
    post_product_html,
    post_tip_html,
    post_top_week_html,
)

logger = logging.getLogger(__name__)


async def _send_photo(bot: Bot, chat_id: str | int, image: str, caption: str, reply_markup) -> bool:
    """Отправляет фото с подписью в канал (graceful fallback без фото)."""
    try:
        await bot.send_photo(
            chat_id, photo=image, caption=caption, reply_markup=reply_markup, parse_mode="HTML"
        )
        return True
    except TelegramForbiddenError:
        logger.error("Бот не имеет доступа к каналу %s. Проверьте права.", chat_id)
        return False
    except (TelegramBadRequest, Exception) as exc:  # noqa: BLE001
        # Фото может быть недоступно — отправляем текстом
        logger.warning("Не удалось отправить фото (%s), отправляю текст", exc)
        try:
            await bot.send_message(chat_id, caption, reply_markup=reply_markup, parse_mode="HTML")
            return True
        except Exception:  # noqa: BLE001
            logger.exception("Не удалось отправить пост")
            return False


async def post_product_to_channel(bot: Bot, slug: str) -> bool:
    """Публикует пост о товаре в канал. Возвращает True при успехе."""
    product = get_product_by_slug(slug)
    if product is None:
        logger.error("Товар %s не найден в каталоге", slug)
        return False
    settings = get_settings()
    chat_id = settings.resolved_channel_id
    caption = post_product_html(product)
    reply_markup = build_product_keyboard(product)
    return await _send_photo(bot, chat_id, product["image"], caption, reply_markup)


async def post_deal(bot: Bot, slug: str, discount_percent: int = 10) -> bool:
    product = get_product_by_slug(slug)
    if product is None:
        return False
    settings = get_settings()
    caption = post_deal_html(product, discount_percent)
    return await _send_photo(
        bot, settings.resolved_channel_id, product["image"], caption, build_product_keyboard(product)
    )


async def post_tip(bot: Bot) -> bool:
    settings = get_settings()
    try:
        await bot.send_message(settings.resolved_channel_id, post_tip_html(), parse_mode="HTML")
        return True
    except Exception:  # noqa: BLE001
        logger.exception("Ошибка поста совета")
        return False


async def post_top_week(bot: Bot) -> bool:
    products = get_products()
    top = sorted(products, key=lambda p: p["price"], reverse=True)[:5]
    settings = get_settings()
    caption = post_top_week_html(top)
    try:
        await bot.send_message(settings.resolved_channel_id, caption, parse_mode="HTML")
        return True
    except Exception:  # noqa: BLE001
        logger.exception("Ошибка поста подборки")
        return False


TEMPLATES = {
    "product": post_product_to_channel,
    "deal": post_deal,
    "tip": post_tip,
    "top_week": post_top_week,
}


async def publish_random(bot: Bot) -> str:
    """Публикует случайный товар из каталога (для планировщика)."""
    products = get_products()
    if not products:
        return "no products"
    product = random.choice(products)
    await post_product_to_channel(bot, product["slug"])
    return product["slug"]
