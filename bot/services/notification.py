"""Уведомления: администраторам и клиентам."""

from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup

from bot.config import get_settings

logger = logging.getLogger(__name__)


async def notify_admins(
    bot: Bot,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: str = "HTML",
) -> None:
    """Рассылает сообщение всем администраторам из ADMIN_IDS."""
    settings = get_settings()
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(admin_id, text, reply_markup=reply_markup, parse_mode=parse_mode)
        except TelegramBadRequest as exc:
            # Пробуем отправить без parse_mode, если текст некорректен
            logger.warning("Не удалось отправить admin_id=%s (parse_mode): %s", admin_id, exc)
            try:
                await bot.send_message(admin_id, text, reply_markup=reply_markup)
            except TelegramBadRequest as inner:
                logger.error("Отправка админу %s полностью не удалась: %s", admin_id, inner)
        except Exception:  # noqa: BLE001
            logger.exception("Ошибка уведомления админа %s", admin_id)


async def notify_manager_group(
    bot: Bot,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: str = "HTML",
) -> bool:
    """Отправляет сообщение в группу менеджеров (MANAGER_GROUP_ID)."""
    settings = get_settings()
    if not settings.manager_group_id:
        return False
    try:
        await bot.send_message(
            settings.manager_group_id, text, reply_markup=reply_markup, parse_mode=parse_mode
        )
        return True
    except Exception:  # noqa: BLE001
        logger.exception("Ошибка отправки в группу менеджеров")
        return False
