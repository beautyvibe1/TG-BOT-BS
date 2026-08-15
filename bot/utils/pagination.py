"""Утилиты пагинации."""

from __future__ import annotations

from collections.abc import Sequence


def paginate(items: Sequence, page: int, page_size: int) -> list:
    """Возвращает срез списка для страницы `page` (1-based)."""
    total_pages = max((len(items) + page_size - 1) // page_size, 1)
    page = max(1, min(page, total_pages))
    start = (page - 1) * page_size
    return list(items[start : start + page_size])


def total_pages(count: int, page_size: int) -> int:
    return max((count + page_size - 1) // page_size, 1)
