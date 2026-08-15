"""Middleware: rate limiting (throttling / anti-spam)."""

from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

# Простой in-memory throttle. Для распределённого — замените на Redis.
_LAST_CALL: dict[int, float] = defaultdict(float)

COOLDOWN_SECONDS = 0.8


class ThrottlingMiddleware(BaseMiddleware):
    """Пропускает не чаще одного сообщения за cooldown-период от одного пользователя."""

    def __init__(self, rate_limit: float = COOLDOWN_SECONDS) -> None:
        self.rate_limit = rate_limit

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_id = getattr(getattr(event, "from_user", None), "id", None)
        if user_id is not None:
            now = time.monotonic()
            if now - _LAST_CALL[user_id] < self.rate_limit:
                # Отвечаем «печатает…» чтобы не спамить, но не обрабатываем
                if isinstance(event, Message):
                    await event.answer_chat_action("typing")
                return None
            _LAST_CALL[user_id] = now
        return await handler(event, data)


def throttling_middleware() -> ThrottlingMiddleware:
    return ThrottlingMiddleware()
