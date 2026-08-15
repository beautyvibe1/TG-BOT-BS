"""Хэндлеры каталога: категории, карточки, поиск, пагинация."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineQuery, InlineQueryResultArticle, InputTextMessageContent, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.config import get_settings
from bot.keyboards.factories import CatalogCallback, MenuCallback, ProductCallback
from bot.keyboards.inline import categories_keyboard, product_keyboard, products_keyboard
from bot.services.catalog import (
    get_category_by_id,
    get_product_by_id,
    get_products,
    search_products,
)
from bot.utils.formatting import product_card

logger = logging.getLogger(__name__)

router = Router(name="catalog")


async def show_product(message: Message, product_id: int, *, edit: bool = True) -> None:
    """Показывает карточку товара с фото и кнопками."""
    product = get_product_by_id(product_id)
    if product is None:
        await message.answer("😔 Товар не найден.")
        return
    text = product_card(product)
    if edit:
        await message.edit_text(text, reply_markup=product_keyboard(product_id), parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=product_keyboard(product_id), parse_mode="HTML")


@router.message(Command("catalog"))
@router.message(F.text == "🛍 Каталог")
async def catalog_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("🛍 <b>Каталог</b>\n\nВыберите категорию:", reply_markup=categories_keyboard(), parse_mode="HTML")


@router.callback_query(CatalogCallback.filter(F.action == "show"))
async def show_category(callback: CallbackQuery, callback_data: CatalogCallback) -> None:
    if not callback_data.category:
        await callback.message.edit_text(
            "🛍 <b>Каталог</b>\n\nВыберите категорию:", reply_markup=categories_keyboard(), parse_mode="HTML"
        )
        await callback.answer()
        return
    await callback.message.edit_text(
        "Выбирайте товар 👇", reply_markup=products_keyboard(callback_data.category, 1), parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(CatalogCallback.filter(F.action == "page"))
async def catalog_page(callback: CallbackQuery, callback_data: CatalogCallback) -> None:
    await callback.message.edit_text(
        "Выбирайте товар 👇", reply_markup=products_keyboard(callback_data.category, callback_data.page), parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(ProductCallback.filter(F.action == "view"))
async def view_product(callback: CallbackQuery, callback_data: ProductCallback) -> None:
    await show_product(callback.message, callback_data.product_id)
    await callback.answer()


@router.callback_query(ProductCallback.filter(F.action == "list"))
async def back_to_list(callback: CallbackQuery, callback_data: ProductCallback) -> None:
    product = get_product_by_id(callback_data.product_id)
    category = product.get("category", "all") if product else "all"
    await callback.message.edit_text("Выбирайте товар 👇", reply_markup=products_keyboard(category, 1), parse_mode="HTML")
    await callback.answer()


@router.callback_query(ProductCallback.filter(F.action == "ask"))
async def ask_product(callback: CallbackQuery, callback_data: ProductCallback, state: FSMContext) -> None:
    from .consultation import start_consultation

    product = get_product_by_id(callback_data.product_id)
    topic = (product.get("ruName") or product["name"]) if product else None
    await start_consultation(callback.message, state, topic=topic)
    await callback.answer()


# ─────────────────────────────────────────────────────────────────────
# Inline-поиск
# ─────────────────────────────────────────────────────────────────────
@router.inline_query()
async def inline_search(inline_query: InlineQuery) -> None:
    query = inline_query.query or ""
    results = search_products(query)
    if not results:
        results = get_products()[:10]

    articles = [
        InlineQueryResultArticle(
            id=str(p["id"]),
            title=p.get("ruName") or p["name"],
            description=f"{p['brand']} · {p['price']:,} ₽".replace(",", " "),
            input_message_content=InputTextMessageContent(
                message_text=f"🛍 {p.get('ruName') or p['name']} — {p['price']:,} ₽".replace(",", " ") + "\nОткройте карточку в каталоге",
            ),
            url=p["image"],
            thumb_url=p["image"],
        )
        for p in results[:30]
    ]
    await inline_query.answer(articles, cache_time=60, is_personal=True)
