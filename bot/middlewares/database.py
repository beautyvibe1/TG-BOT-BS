"""Middleware: внедрение async-сессии БД в контекст хэндлеров."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from bot.database import get_sessionmaker


class DatabaseMiddleware(BaseMiddleware):
    """Открывает сессию на событие, закрывает после обработки."""

    def __init__(self, session_pool) -> None:
        self.session_pool = session_pool

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with self.session_pool() as session:
            data["session"] = session
            try:
                return await handler(event, data)
            finally:
                await session.close()


def db_session_middleware():
    return DatabaseMiddleware(get_sessionmaker())
