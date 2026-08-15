"""Общие хэндлеры: help, about, акции, доставка, отмена."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import get_settings
from bot.keyboards.factories import MenuCallback
from bot.keyboards.inline import promos_keyboard
from bot.services.catalog import get_delivery, get_promos, get_reviews
from bot.utils.formatting import about_text, delivery_text

logger = logging.getLogger(__name__)

router = Router(name="common")


async def show_promos(message: Message) -> None:
    promos = get_promos()
    lines = ["🔥 <b>Акции и предложения</b>", ""]
    if promos:
        for promo in promos:
            lines.append(f"{promo.get('emoji', '✨')} <b>{promo['title']}</b>")
            lines.append(promo["text"])
            lines.append("")
    else:
        lines.append("Сейчас действует акция «Предзаказ из США» — привезём любой товар под заказ.")
        lines.append("")
    lines.append("Промокоды появляются в корзине при оформлении заказа 🎟")
    await message.edit_text("\n".join(lines), reply_markup=promos_keyboard(), parse_mode="HTML")


@router.message(F.text == "🔥 Акции")
async def promos_message(message: Message) -> None:
    await message.answer(
        "🔥 <b>Акции и предложения</b>\n\n"
        + _promos_text(),
        reply_markup=promos_keyboard(), parse_mode="HTML",
    )


def _promos_text() -> str:
    parts = []
    for promo in get_promos():
        parts.append(f"{promo.get('emoji', '✨')} <b>{promo['title']}</b>\n{promo['text']}")
    if not parts:
        parts.append("Предзаказ из США — привезём любой товар под заказ. Уточняйте у менеджера.")
    return "\n\n".join(parts)


@router.message(F.text == "📍 Доставка и оплата")
async def delivery_message(message: Message) -> None:
    await message.answer(delivery_text(), parse_mode="HTML")


@router.message(F.text == "ℹ️ О магазине")
async def about_message(message: Message) -> None:
    settings = get_settings()
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.button(text="🌐 Сайт", url=settings.site_url)
    builder.button(text="🤝 Avito", url=settings.avito_url)
    builder.button(text="📢 Канал", url=settings.channel_url)
    builder.button(text="📧 Написать", url=f"mailto:{settings.support_email}")
    builder.adjust(2)
    await message.answer(about_text(), reply_markup=builder.as_markup(), parse_mode="HTML")


@router.message(Command("cancel", "отмена"))
async def cancel_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Действие отменено. Чем могу помочь?", reply_markup=__import__(
        "bot.keyboards", fromlist=["main_menu_keyboard"]
    ).main_menu_keyboard())


# ─────────────────────────────────────────────────────────────────────
# Неизвестные команды
# ─────────────────────────────────────────────────────────────────────
@router.message()
async def unknown_text(message: Message, state: FSMContext) -> None:
    """Catch-all: любое нераспознанное сообщение."""
    from bot.keyboards import main_menu_keyboard

    text = message.text or message.caption or ""
    if text.strip().lower() in ("привет", "hi", "здравствуйте", "hello"):
        await message.answer("👋 Привет! Чем помочь? Выберите пункт в меню.", reply_markup=main_menu_keyboard())
        return
    if text.startswith("/"):
        await message.answer("Неизвестная команда. Используйте меню ниже.", reply_markup=main_menu_keyboard())
        return
    await message.answer(
        "Я не совсем понял 😅\nВыберите раздел в меню ниже — я помогу с каталогом, заказом и консультацией.",
        reply_markup=main_menu_keyboard(),
    )
