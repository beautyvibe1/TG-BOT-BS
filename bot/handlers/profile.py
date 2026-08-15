"""Профиль пользователя: настройки, мои заказы, адрес доставки."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.factories import MenuCallback, OrderCallback
from bot.keyboards.inline import order_status_keyboard, orders_keyboard
from bot.models import Order
from bot.services.catalog import get_or_create_user
from bot.services.order import render_order
from bot.states import OrderState

logger = logging.getLogger(__name__)

router = Router(name="profile")


async def show_orders(message: Message, session, chat_id: int) -> None:
    user = await get_or_create_user(session, message.from_user.id)
    from sqlalchemy import select

    orders = (
        await session.scalars(
            select(Order).where(Order.user_id == user.id).order_by(Order.created_at.desc()).limit(10)
        )
    ).all()
    if not orders:
        text = "📦 <b>У вас пока нет заказов.</b>\n\nЗагляните в каталог и сделайте первый заказ!"
        kb = __import__("bot.keyboards.inline", fromlist=["cart_keyboard"]).cart_keyboard([], can_checkout=False)
        from bot.keyboards.factories import MenuCallback
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()
        builder.button(text="🛍 В каталог", callback_data=MenuCallback(action="catalog").pack())
        await message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
        return
    await message.edit_text("📦 <b>Мои заказы:</b>", reply_markup=orders_keyboard(list(orders)), parse_mode="HTML")


@router.message(F.text == "📦 Мои заказы")
async def orders_message(message: Message, session) -> None:
    user = await get_or_create_user(session, message.from_user.id)
    from sqlalchemy import select

    orders = (
        await session.scalars(
            select(Order).where(Order.user_id == user.id).order_by(Order.created_at.desc()).limit(10)
        )
    ).all()
    if not orders:
        await message.answer("📦 <b>У вас пока нет заказов.</b>\n\nЗагляните в каталог!", parse_mode="HTML")
        return
    await message.answer("📦 <b>Мои заказы:</b>", reply_markup=orders_keyboard(list(orders)), parse_mode="HTML")


@router.callback_query(OrderCallback.filter(F.action == "status"))
async def order_detail(callback: CallbackQuery, callback_data: OrderCallback, session) -> None:
    order = await session.get(Order, int(callback_data.value))
    if order is None:
        await callback.answer("Заказ не найден")
        return
    can_pay = order.payment_status in ("pending", "failed") and order.status == "new"
    kb = order_status_keyboard(order.id) if can_pay else None
    await callback.message.edit_text(render_order(order), reply_markup=kb, parse_mode="Markdown")
    await callback.answer()


@router.message(F.text == "⚙️ Настройки")
async def settings_menu(message: Message, session) -> None:
    user = await get_or_create_user(
        session, message.from_user.id, username=message.from_user.username,
        first_name=message.from_user.first_name, last_name=message.from_user.last_name,
    )
    text = (
        "⚙️ <b>Настройки</b>\n\n"
        f"👤 Профиль: {user.full_name or user.tg_id}\n"
        f"📞 Телефон: {user.default_phone or 'не указан'}\n"
        f"📍 Адрес: {user.default_address or 'не указан'}\n"
        f"🔔 Уведомления: {'включены' if user.is_subscribed else 'выключены'}\n\n"
        "Настройки обновляются автоматически при оформлении заказа."
    )
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from bot.keyboards.factories import MenuCallback

    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 В меню", callback_data=MenuCallback(action="main").pack())
    await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")
