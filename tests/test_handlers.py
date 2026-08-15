"""Тесты хэндлеров и клавиатур."""

from __future__ import annotations

from aiogram import Dispatcher

from bot.keyboards import categories_keyboard, main_menu_keyboard, products_keyboard
from bot.main import create_dispatcher
from bot.utils.formatting import product_card


def test_dispatcher_builds():
    dp = create_dispatcher()
    assert isinstance(dp, Dispatcher)
    # Проверяем, что роутеры подключены
    from bot.handlers import register_routers  # noqa: F401
    # В aiogram 3.x дочерние роутеры доступны через dp.sub_routers
    assert len(dp.sub_routers) > 0


def test_main_menu_keyboard():
    kb = main_menu_keyboard()
    buttons = [b.text for row in kb.keyboard for b in row]
    assert "🛍 Каталог" in buttons
    assert "🛒 Корзина" in buttons


def test_categories_keyboard():
    kb = categories_keyboard()
    texts = [b.text for row in kb.inline_keyboard for b in row]
    assert any("Уход" in t for t in texts)
    assert any("Все товары" in t for t in texts)


def test_products_keyboard_has_items():
    kb = products_keyboard("care", 1)
    texts = [b.text for row in kb.inline_keyboard for b in row]
    assert any("Лифтинг" in t or "Крем" in t for t in texts)


def test_product_card_format():
    from bot.services.catalog import get_products

    card = product_card(get_products()[0])
    assert "₽" in card
    assert "<b>" in card
