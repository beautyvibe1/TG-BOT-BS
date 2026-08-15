"""Хэндлеры корзины."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.factories import CartCallback, MenuCallback, ProductCallback
from bot.keyboards.inline import cart_item_actions, cart_keyboard, product_qty_keyboard
from bot.services import catalog as catalog_service
from bot.services.cart import render_cart
from bot.services.catalog import get_or_create_user

logger = logging.getLogger(__name__)

router = Router(name="cart")


async def show_cart(message: Message, session, chat_id: int) -> None:
    user = await get_or_create_user(
        session, message.from_user.id, username=message.from_user.username,
        first_name=message.from_user.first_name, last_name=message.from_user.last_name,
    )
    cart = await catalog_service.get_cart(session, user)
    text = render_cart(cart)
    reply = cart_keyboard(cart.items, can_checkout=bool(cart.items))
    await message.edit_text(text, reply_markup=reply, parse_mode="Markdown")


@router.message(F.text == "🛒 Корзина")
async def show_cart_message(message: Message, state: FSMContext, session) -> None:
    await state.clear()
    user = await get_or_create_user(
        session, message.from_user.id, username=message.from_user.username,
        first_name=message.from_user.first_name, last_name=message.from_user.last_name,
    )
    cart = await catalog_service.get_cart(session, user)
    await message.answer(render_cart(cart), reply_markup=cart_keyboard(cart.items, can_checkout=bool(cart.items)), parse_mode="Markdown")


@router.callback_query(MenuCallback.filter(F.action == "cart"))
async def cart_from_menu(callback: CallbackQuery, session) -> None:
    await show_cart(callback.message, session, callback.message.chat.id)
    await callback.answer()


@router.callback_query(CartCallback.filter(F.action == "view"))
async def cart_view(callback: CallbackQuery, session) -> None:
    await show_cart(callback.message, session, callback.message.chat.id)
    await callback.answer()


@router.callback_query(CartCallback.filter(F.action == "view_item"))
async def cart_view_item(callback: CallbackQuery, callback_data: CartCallback, session) -> None:
    user = await get_or_create_user(session, callback.from_user.id)
    cart = await catalog_service.get_cart(session, user)
    item = next((i for i in cart.items if i.id == callback_data.item_id), None)
    if item is None:
        await callback.answer("Позиция не найдена", show_alert=True)
        return
    product = item.product
    text = (
        f"<b>{product.ru_name or product.name}</b>\n"
        f"{product.brand}\n"
        f"Цена: <b>{product.price:,} ₽</b>".replace(",", " ") +
        f"\nКоличество: {item.quantity}\n"
        f"Итого: <b>{item.line_total:,} ₽</b>".replace(",", " ")
    )
    await callback.message.edit_text(text, reply_markup=cart_item_actions(item.id), parse_mode="HTML")
    await callback.answer()


@router.callback_query(ProductCallback.filter(F.action == "add"))
async def add_to_cart(callback: CallbackQuery, callback_data: ProductCallback, session) -> None:
    user = await get_or_create_user(session, callback.from_user.id)
    try:
        await catalog_service.add_to_cart(session, user, callback_data.product_id, quantity=1)
    except ValueError as exc:
        await callback.answer(str(exc), show_alert=True)
        return
    await callback.answer("✅ Добавлено в корзину", show_alert=False)
    await callback.message.answer("Товар в корзине. Изменить количество?", reply_markup=product_qty_keyboard(callback_data.product_id))


@router.callback_query(ProductCallback.filter(F.action == "dec"))
async def dec_product_qty(callback: CallbackQuery, callback_data: ProductCallback, session) -> None:
    await _adjust_product_qty(callback, callback_data.product_id, -1, session)


@router.callback_query(ProductCallback.filter(F.action == "remove"))
async def remove_from_cart(callback: CallbackQuery, callback_data: ProductCallback, session) -> None:
    user = await get_or_create_user(session, callback.from_user.id)
    cart = await catalog_service.get_cart(session, user)
    item = _find_item(cart, callback_data.product_id)
    if item:
        await catalog_service.remove_cart_item(session, item.id)
        await callback.answer("🗑 Удалено")
    await show_cart(callback.message, session, callback.message.chat.id)


def _find_item(cart, product_id: int):
    """Ищет позицию корзины по id каталога (external_id) или по первичному ключу."""
    return next(
        (
            i
            for i in cart.items
            if i.product_id == product_id
            or (i.product is not None and i.product.external_id == product_id)
        ),
        None,
    )


async def _adjust_product_qty(callback: CallbackQuery, product_id: int, delta: int, session) -> None:
    user = await get_or_create_user(session, callback.from_user.id)
    cart = await catalog_service.get_cart(session, user)
    item = _find_item(cart, product_id)
    if item is None:
        await callback.answer("Товара нет в корзине")
        return
    new_qty = item.quantity + delta
    if new_qty <= 0:
        await catalog_service.remove_cart_item(session, item.id)
        await callback.answer("Удалено")
    else:
        await catalog_service.update_cart_item(session, item.id, new_qty)
        await callback.answer(f"Количество: {new_qty}")
    await show_cart(callback.message, session, callback.message.chat.id)


@router.callback_query(CartCallback.filter(F.action == "inc"))
async def inc_item(callback: CallbackQuery, callback_data: CartCallback, session) -> None:
    user = await get_or_create_user(session, callback.from_user.id)
    cart = await catalog_service.get_cart(session, user)
    target = next((i for i in cart.items if i.id == callback_data.item_id), None)
    if target:
        await catalog_service.update_cart_item(session, target.id, target.quantity + 1)
    await show_cart(callback.message, session, callback.message.chat.id)
    await callback.answer()


@router.callback_query(CartCallback.filter(F.action == "dec"))
async def dec_item(callback: CallbackQuery, callback_data: CartCallback, session) -> None:
    user = await get_or_create_user(session, callback.from_user.id)
    cart = await catalog_service.get_cart(session, user)
    target = next((i for i in cart.items if i.id == callback_data.item_id), None)
    if target:
        if target.quantity <= 1:
            await catalog_service.remove_cart_item(session, target.id)
        else:
            await catalog_service.update_cart_item(session, target.id, target.quantity - 1)
    await show_cart(callback.message, session, callback.message.chat.id)
    await callback.answer()


@router.callback_query(CartCallback.filter(F.action == "remove"))
async def remove_item(callback: CallbackQuery, callback_data: CartCallback, session) -> None:
    await catalog_service.remove_cart_item(session, callback_data.item_id)
    await show_cart(callback.message, session, callback.message.chat.id)
    await callback.answer()


@router.callback_query(CartCallback.filter(F.action == "clear"))
async def clear_cart(callback: CallbackQuery, session) -> None:
    user = await get_or_create_user(session, callback.from_user.id)
    await catalog_service.clear_cart(session, user)
    await callback.answer("🗑 Корзина очищена")
    await show_cart(callback.message, session, callback.message.chat.id)


@router.callback_query(CartCallback.filter(F.action == "checkout"))
async def checkout(callback: CallbackQuery, state: FSMContext, session) -> None:
    from .order import start_order

    await start_order(callback, state, session)
    await callback.answer()


@router.callback_query(CartCallback.filter(F.action == "promo"))
async def promo_input(callback: CallbackQuery, state: FSMContext) -> None:
    from bot.states import OrderState

    await state.set_state(OrderState.PROMO)
    await callback.message.answer("🎟 Введите промокод:\n\n/отмена — чтобы отменить")
    await callback.answer()
