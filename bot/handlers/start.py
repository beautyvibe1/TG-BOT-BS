"""Хэндлеры: /start, главное меню, deep-link маршрутизация."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.types import User as TgUser

from bot.config import get_settings
from bot.keyboards import main_inline_menu, main_menu_keyboard
from bot.keyboards.factories import MenuCallback
from bot.services.catalog import get_or_create_user, get_product_by_slug

logger = logging.getLogger(__name__)

router = Router(name="start")

START_TEXT = (
    "✨ <b>Beauty Supply MSK</b> — премиальная косметика из США.\n\n"
    "Проверяем оригинальность, подбираем как beauty-консьерж и доставляем "
    "в любой город России.\n\n"
    "Выберите раздел меню ниже 👇"
)


def _resolve_payload(payload: str | None) -> tuple[str, str | None]:
    """Разбирает deep-link payload. Возвращает (action, value)."""
    if not payload:
        return "main", None
    # UTM-источники
    if payload.startswith("src_"):
        parts = payload.split("_", 2)
        source = parts[1] if len(parts) > 1 else ""
        rest = parts[2] if len(parts) > 2 else ""
        return "source", f"{source}:{rest}"
    if payload.startswith("product_"):
        return "product", payload.removeprefix("product_")
    if payload.startswith("cat_"):
        return "catalog", payload.removeprefix("cat_")
    if payload.startswith("lead_") or payload == "question" or payload == "lead_repeat":
        return "consult", payload
    if payload == "preorder_usa":
        return "promos", None
    # Возможно slug товара
    if get_product_by_slug(payload):
        return "product", payload
    return "main", None


async def _track_source(user: TgUser, payload: str | None, session) -> None:
    """Записывает источник перехода в профиль пользователя."""
    if not payload:
        return
    db_user = await get_or_create_user(session, user.id, username=user.username,
                                       first_name=user.first_name, last_name=user.last_name)
    if payload.startswith("src_"):
        db_user.last_source = payload.split("_")[1] if len(payload.split("_")) > 1 else "unknown"
    elif payload.startswith("product_"):
        db_user.last_source = "site"
    db_user.last_payload = payload[:256]
    await session.commit()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, session) -> None:
    await state.clear()
    parts = (message.text or "").strip().split(maxsplit=1)
    payload = parts[1].strip() if len(parts) > 1 else ""

    try:
        await _track_source(message.from_user, payload or None, session)
    except Exception:  # noqa: BLE001
        logger.exception("Не удалось сохранить источник")

    action, value = _resolve_payload(payload or None)

    if action == "product" and value:
        product = get_product_by_slug(value)
        if product:
            from bot.handlers.catalog import show_product

            await show_product(message, product_id=product["id"], edit=False)
            return

    if action == "catalog":
        from bot.keyboards.inline import categories_keyboard, products_keyboard

        if value:
            await message.answer(
                "Выбирайте товар 👇", reply_markup=products_keyboard(value, 1), parse_mode="HTML"
            )
        else:
            await message.answer(
                "🛍 <b>Каталог</b>\n\nВыберите категорию:",
                reply_markup=categories_keyboard(),
                parse_mode="HTML",
            )
        return

    if action == "consult":
        from bot.keyboards.inline import consultation_keyboard

        await message.answer(
            "💬 <b>Консультация</b>\n\nНаш beauty-консьерж поможет подобрать уход. Выберите вариант:",
            reply_markup=consultation_keyboard(),
            parse_mode="HTML",
        )
        return

    if action == "promos":
        from bot.keyboards.inline import promos_keyboard
        from bot.services.catalog import get_promos

        lines = ["🔥 <b>Акции и предложения</b>", ""]
        for promo in get_promos():
            lines.append(f"{promo.get('emoji', '✨')} <b>{promo['title']}</b>\n{promo['text']}")
            lines.append("")
        if len(lines) == 2:
            lines.append("Предзаказ из США — привезём любой товар под заказ. Уточняйте у менеджера.")
            lines.append("")
        await message.answer("\n".join(lines), reply_markup=promos_keyboard(), parse_mode="HTML")
        return

    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\n\n" + START_TEXT,
        reply_markup=main_menu_keyboard(),
    )
    await message.answer("Чем займёмся?", reply_markup=main_inline_menu())


@router.message(Command("menu", "help"))
async def cmd_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(START_TEXT, reply_markup=main_menu_keyboard())
    await message.answer("Чем займёмся?", reply_markup=main_inline_menu())


@router.message(F.text.in_({"🔙 Назад", "/start"}))
async def back_to_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(START_TEXT, reply_markup=main_menu_keyboard())
    await message.answer("Чем займёмся?", reply_markup=main_inline_menu())


@router.callback_query(MenuCallback.filter(F.action == "main"))
async def menu_main(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(START_TEXT, reply_markup=main_inline_menu())
    await callback.answer()


@router.callback_query(MenuCallback.filter(F.action == "catalog"))
async def menu_catalog(callback: CallbackQuery) -> None:
    from bot.keyboards.inline import categories_keyboard

    await callback.message.edit_text("🛍 <b>Каталог</b>\n\nВыберите категорию:", reply_markup=categories_keyboard())
    await callback.answer()


@router.callback_query(MenuCallback.filter(F.action == "cart"))
async def menu_cart(callback: CallbackQuery, session) -> None:
    from bot.handlers.cart import show_cart

    await show_cart(callback.message, session, callback.message.chat.id)
    await callback.answer()


@router.callback_query(MenuCallback.filter(F.action == "orders"))
async def menu_orders(callback: CallbackQuery, session) -> None:
    from bot.handlers.profile import show_orders

    await show_orders(callback.message, session, callback.message.chat.id)
    await callback.answer()


@router.callback_query(MenuCallback.filter(F.action == "consult"))
async def menu_consult(callback: CallbackQuery) -> None:
    from bot.handlers.consultation import show_consultation_menu

    await show_consultation_menu(callback.message)
    await callback.answer()


@router.callback_query(MenuCallback.filter(F.action == "promos"))
async def menu_promos(callback: CallbackQuery) -> None:
    from bot.handlers.common import show_promos

    await show_promos(callback.message)
    await callback.answer()


@router.callback_query(MenuCallback.filter(F.action == "delivery"))
async def menu_delivery(callback: CallbackQuery) -> None:
    from bot.utils.formatting import delivery_text

    await callback.message.edit_text(delivery_text(), reply_markup=main_inline_menu())
    await callback.answer()


@router.callback_query(MenuCallback.filter(F.action == "about"))
async def menu_about(callback: CallbackQuery) -> None:
    from bot.keyboards.inline import InlineKeyboardBuilder
    from bot.utils.formatting import about_text

    settings = get_settings()
    builder = InlineKeyboardBuilder()
    builder.button(text="🌐 Сайт", url=settings.site_url)
    builder.button(text="🤝 Avito", url=settings.avito_url)
    builder.button(text="📢 Канал", url=settings.channel_url)
    builder.button(text="🔙 В меню", callback_data=MenuCallback(action="main").pack())
    builder.adjust(3)
    await callback.message.edit_text(about_text(), reply_markup=builder.as_markup())
    await callback.answer()
