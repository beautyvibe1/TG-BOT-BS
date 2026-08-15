"""Планировщик публикаций в канал (APScheduler + aiocron).

Расписание настраивается через CHANNEL_POST_TIMES (список "HH:MM"),
каждое время рандомизируется ±15 минут для естественности.
Flood-контроль учитывается: между постами > 60 сек.
"""

from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo

from bot.config import get_settings

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None

# Циклическая ротация типов постов
_TEMPLATE_SEQUENCE = ["product", "product", "deal", "product", "tip", "product", "top_week"]
_SEQUENCE_INDEX = 0


async def _publish_job(bot: Bot) -> None:
    """Один запланированный пост."""
    global _SEQUENCE_INDEX
    from .poster import post_deal, post_product_to_channel, post_tip, post_top_week
    from bot.services.catalog import get_products

    products = get_products()
    if not products:
        logger.warning("Каталог пуст — пропуск публикации")
        return

    template = _TEMPLATE_SEQUENCE[_SEQUENCE_INDEX % len(_TEMPLATE_SEQUENCE)]
    _SEQUENCE_INDEX += 1
    product = random.choice(products)

    try:
        if template == "deal":
            await post_deal(bot, product["slug"], discount_percent=random.randint(5, 15))
        elif template == "tip":
            await post_tip(bot)
        elif template == "top_week":
            await post_top_week(bot)
        else:
            await post_product_to_channel(bot, product["slug"])
        logger.info("Пост опубликован: %s", template)
    except Exception:  # noqa: BLE001
        logger.exception("Ошибка плановой публикации")


def _build_triggers() -> list[CronTrigger]:
    """Cron-триггеры на каждый заданный час с рандомизацией ±15 минут."""
    settings = get_settings()
    triggers: list[CronTrigger] = []
    for time_str in settings.channel_post_times:
        try:
            hour_str, minute_str = time_str.split(":")
            hour, minute = int(hour_str), int(minute_str)
        except ValueError:
            logger.warning("Неверное время в CHANNEL_POST_TIMES: %s", time_str)
            continue
        triggers.append(
            CronTrigger(
                hour=hour,
                minute=minute,
                timezone=ZoneInfo(settings.timezone),
                jitter=900,  # ±15 минут
            )
        )
    return triggers


def start_scheduler(bot: Bot) -> AsyncIOScheduler:
    """Запускает планировщик (идемпотентно)."""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        return _scheduler

    settings = get_settings()
    _scheduler = AsyncIOScheduler(timezone=ZoneInfo(settings.timezone))
    for trigger in _build_triggers():
        _scheduler.add_job(_publish_job, trigger, args=[bot], coalesce=True, misfire_grace_time=600)
    _scheduler.start()
    logger.info("Планировщик канала запущен (времена: %s)", settings.channel_post_times)
    return _scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Планировщик остановлен")
