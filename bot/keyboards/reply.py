"""ReplyKeyboard: главное меню."""

from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню бота (ReplyKeyboard)."""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="🛍 Каталог"))
    builder.row(KeyboardButton(text="🛒 Корзина"), KeyboardButton(text="📦 Мои заказы"))
    builder.row(KeyboardButton(text="💬 Консультация"), KeyboardButton(text="🔥 Акции"))
    builder.row(KeyboardButton(text="📍 Доставка и оплата"), KeyboardButton(text="ℹ️ О магазине"))
    builder.row(KeyboardButton(text="⚙️ Настройки"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True, input_field_placeholder="Выберите раздел меню…")


def remove_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с одной кнопкой «Назад»."""
    builder = ReplyKeyboardBuilder()
    builder.button(text="🔙 Назад")
    return builder.as_markup(resize_keyboard=True)


def contact_keyboard() -> ReplyKeyboardMarkup:
    """Запрос номера телефона."""
    builder = ReplyKeyboardBuilder()
    builder.button(text="📱 Отправить номер", request_contact=True)
    builder.button(text="🔙 Назад")
    return builder.as_markup(resize_keyboard=True)
