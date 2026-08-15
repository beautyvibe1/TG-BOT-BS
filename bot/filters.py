"""Кастомные фильтры aiogram."""

from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from bot.config import get_settings


class IsAdmin(BaseFilter):
    """Пропускает только сообщения от администраторов."""

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        user = event.from_user
        if user is None:
            return False
        return get_settings().is_admin(user.id)


class ChatIsManagerGroup(BaseFilter):
    """Пропускает только сообщения из группы менеджеров (MANAGER_GROUP_ID)."""

    async def __call__(self, event: Message) -> bool:
        group_id = get_settings().manager_group_id
        if group_id is None or event.chat is None:
            return False
        return event.chat.id == group_id
