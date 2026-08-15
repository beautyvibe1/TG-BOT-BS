"""Сборка приложения: bot + dispatcher + middlewares + storage."""

from __future__ import annotations

import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage

from bot.config import get_settings
from bot.handlers import register_routers
from bot.middlewares import (
    db_session_middleware,
    logging_middleware,
    throttling_middleware,
)

logger = logging.getLogger(__name__)


def setup_logging(level: str | None = None) -> None:
    import sys

    from loguru import logger as _logger

    level = (level or get_settings().log_level or "INFO").upper()
    _logger.remove()
    _logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <7}</level> | <cyan>{name}</cyan> | {message}",
    )
    # Прокидываем логгер loguru в стандартное logging
    import logging as std_logging

    class InterceptHandler(std_logging.Handler):
        def emit(self, record: std_logging.LogRecord) -> None:
            try:
                _logger.opt(depth=6, exception=record.exc_info).log(record.levelname, record.getMessage())
            except Exception:  # noqa: BLE001
                _logger.opt(exception=True).error("Ошибка логирования")

    std_logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)


def _redis_reachable(url: str, timeout: float = 1.0) -> bool:
    """Быстрая проверка доступности Redis по TCP (для fallback на MemoryStorage)."""
    try:
        import socket
        from urllib.parse import urlparse

        parsed = urlparse(url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 6379
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def build_storage():
    settings = get_settings()
    if settings.use_redis:
        if not _redis_reachable(settings.redis_url):
            logger.warning("Redis недоступен (%s), использую MemoryStorage", settings.redis_url)
            return MemoryStorage()
        try:
            from redis.asyncio import Redis

            redis = Redis.from_url(settings.redis_url, decode_responses=True)
            storage = RedisStorage(redis)
            logger.info("FSM storage: Redis (%s)", settings.redis_url)
            return storage
        except Exception:  # noqa: BLE001
            logger.warning("Не удалось создать RedisStorage, использую MemoryStorage")
    return MemoryStorage()


def create_bot() -> Bot:
    settings = get_settings()
    return Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=build_storage())

    # Middlewares
    dp.update.outer_middleware(logging_middleware())
    dp.message.middleware(db_session_middleware())
    dp.callback_query.middleware(db_session_middleware())
    dp.message.outer_middleware(throttling_middleware())
    dp.callback_query.outer_middleware(throttling_middleware())

    register_routers(dp)
    return dp


async def on_startup(bot: Bot) -> None:
    """Инициализация при запуске: БД, каталог, планировщик."""
    from bot.database import get_sessionmaker, init_db
    from bot.services import catalog

    await init_db()
    async with get_sessionmaker()() as session:
        await catalog.seed_database(session)

    # Планировщик канала
    settings = get_settings()
    if settings.channel_posting_enabled:
        try:
            from channel.scheduler import start_scheduler

            start_scheduler(bot)
            logger.info("Планировщик канала запущен")
        except Exception:  # noqa: BLE001
            logger.exception("Не удалось запустить планировщик канала")


async def on_shutdown(bot: Bot) -> None:
    """Graceful shutdown."""
    from bot.database import close_db

    try:
        await bot.session.close()
    except Exception:  # noqa: BLE001
        pass
    await close_db()
    logger.info("Приложение остановлено")
