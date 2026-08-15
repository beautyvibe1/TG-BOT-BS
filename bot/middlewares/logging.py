"""Middleware: логирование событий и обработка ошибок."""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

logger = logging.getLogger("bot.requests")


class LoggingMiddleware(BaseMiddleware):
    """Логирует входящие события и время обработки."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        started = time.monotonic()
        user = getattr(event, "from_user", None)
        user_repr = f"@{user.username}" if user and user.username else getattr(user, "id", "?")
        try:
            result = await handler(event, data)
            elapsed = (time.monotonic() - started) * 1000
            logger.info("OK user=%s elapsed=%.1fms event=%s", user_repr, elapsed, type(event).__name__)
            return result
        except Exception:  # noqa: BLE001
            elapsed = (time.monotonic() - started) * 1000
            logger.exception("ERROR user=%s elapsed=%.1fms event=%s", user_repr, elapsed, type(event).__name__)
            # Пробуем сообщить пользователю о сбое
            if isinstance(event, Message):
                try:
                    await event.answer("😔 Произошла ошибка. Попробуйте ещё раз или позже.")
                except Exception:  # noqa: BLE001
                    pass
            raise


def logging_middleware() -> LoggingMiddleware:
    return LoggingMiddleware()
