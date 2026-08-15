"""Оформление заказа: FSM-сценарий."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.factories import CartCallback, OrderCallback
from bot.keyboards.inline import (
    delivery_methods_keyboard,
    order_confirm_keyboard,
    payment_methods_keyboard,
)
from bot.models import Order, PaymentMethod
from bot.services import catalog as catalog_service
from bot.services.cart import get_promo
from bot.services.catalog import get_or_create_user
from bot.services.notification import notify_admins, notify_manager_group
from bot.services.order import (
    create_order_from_cart,
    method_label,
    payment_label,
    render_order,
)
from bot.states import OrderState

logger = logging.getLogger(__name__)

router = Router(name="order")

DELIVERY_COSTS = {"moscow_courier": 500, "cdek": 350, "avito_delivery": 0, "self_pickup": 0}

ONLINE_PAYMENT = {PaymentMethod.CARD.value, PaymentMethod.SB_P.value, PaymentMethod.TELEGRAM_STARS.value}


async def start_order(callback: CallbackQuery, state: FSMContext, session) -> None:
    """Начало оформления (из корзины)."""
    user = await get_or_create_user(session, callback.from_user.id)
    cart = await catalog_service.get_cart(session, user)
    if not cart.items:
        await callback.answer("Корзина пуста", show_alert=True)
        return
    await state.set_state(OrderState.NAME)
    await state.update_data(cart_user_id=user.id, promo_code=None, discount=0)
    await callback.message.answer(
        "Оформляем заказ ✨\n\n<b>Как к вам обращаться?</b>\n\nВведите имя.\n\n/отмена — отменить",
        parse_mode="HTML",
    )


@router.message(OrderState.NAME)
async def order_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not name or name.startswith("/"):
        return
    await state.update_data(customer_name=name)
    await state.set_state(OrderState.PHONE)
    await message.answer("📱 <b>Куда прислать подтверждение?</b>\n\nВведите номер телефона.", parse_mode="HTML")


@router.message(OrderState.PHONE, F.contact)
async def order_phone_contact(message: Message, state: FSMContext) -> None:
    phone = message.contact.phone_number
    await state.update_data(phone=phone)
    await state.set_state(OrderState.DELIVERY_METHOD)
    await message.answer("🚚 <b>Способ доставки:</b>", reply_markup=delivery_methods_keyboard(), parse_mode="HTML")


@router.message(OrderState.PHONE)
async def order_phone_text(message: Message, state: FSMContext) -> None:
    phone = (message.text or "").strip()
    if not phone or phone.startswith("/"):
        return
    await state.update_data(phone=phone)
    await state.set_state(OrderState.DELIVERY_METHOD)
    await message.answer("🚚 <b>Способ доставки:</b>", reply_markup=delivery_methods_keyboard(), parse_mode="HTML")


@router.callback_query(OrderCallback.filter(F.action == "delivery"), OrderState.DELIVERY_METHOD)
async def order_delivery(callback: CallbackQuery, callback_data: OrderCallback, state: FSMContext) -> None:
    method = callback_data.value
    await state.update_data(delivery_method=method, delivery_cost=DELIVERY_COSTS.get(method, 0))
    await state.set_state(OrderState.ADDRESS)
    await callback.message.edit_text(
        f"✅ Доставка: <b>{method_label(method)}</b>\n\n"
        "📍 <b>Адрес доставки / пункт выдачи:</b>\n\nВведите адрес.\n"
        "(для самовывоза напишите «самовывоз»)",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(OrderState.ADDRESS)
async def order_address(message: Message, state: FSMContext) -> None:
    address = (message.text or "").strip()
    if not address or address.startswith("/"):
        return
    await state.update_data(address=address)
    await state.set_state(OrderState.PAYMENT_METHOD)
    await message.answer("💳 <b>Способ оплаты:</b>", reply_markup=payment_methods_keyboard(), parse_mode="HTML")


@router.callback_query(OrderCallback.filter(F.action == "payment"), OrderState.PAYMENT_METHOD)
async def order_payment(callback: CallbackQuery, callback_data: OrderCallback, state: FSMContext) -> None:
    method = callback_data.value
    data = await state.get_data()
    await state.update_data(payment_method=method)
    await state.set_state(OrderState.CONFIRMATION)

    from bot.keyboards.inline import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    promo_label = "🎟 Изменить промокод" if data.get("promo_code") else "🎟 Ввести промокод"
    builder.button(text=promo_label, callback_data=CartCallback(action="promo").pack())
    builder.button(text="✅ Подтвердить заказ", callback_data=OrderCallback(action="confirm").pack())
    builder.button(text="↩️ В корзину", callback_data=CartCallback(action="view").pack())
    builder.adjust(1)

    await callback.message.edit_text(
        f"💳 Оплата: <b>{payment_label(method)}</b>\n\nГотово к подтверждению. "
        "Можно применить промокод или сразу подтвердить.",
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(OrderCallback.filter(F.action == "confirm"), OrderState.CONFIRMATION)
async def order_confirm(callback: CallbackQuery, state: FSMContext, session) -> None:
    """Предпросмотр заказа и финальное подтверждение."""
    data = await state.get_data()
    user = await catalog_service.get_or_create_user(session, callback.from_user.id)
    cart = await catalog_service.get_cart(session, user)

    promo_code = data.get("promo_code")
    discount = data.get("discount", 0)
    delivery_cost = data.get("delivery_cost", 0)

    preview = [
        "📋 <b>Проверьте заказ:</b>",
        "",
    ]
    for item in cart.items:
        preview.append(f"• {item.product.ru_name or item.product.name} ×{item.quantity}")
    preview += [
        "",
        f"Товары: {cart.total_price:,} ₽".replace(",", " "),
    ]
    if discount:
        preview.append(f"Скидка: −{discount:,} ₽".replace(",", " "))
    if delivery_cost:
        preview.append(f"Доставка: {delivery_cost:,} ₽".replace(",", " "))
    preview.append(f"💎 <b>Итого: {cart.total_price - discount + delivery_cost:,} ₽</b>".replace(",", " "))
    preview += [
        "",
        f"👤 {data.get('customer_name')}",
        f"📞 {data.get('phone')}",
        f"📍 {data.get('address')}",
        f"🚚 {method_label(data.get('delivery_method'))}",
        f"💳 {payment_label(data.get('payment_method'))}",
    ]
    if promo_code:
        preview.append(f"🎟 Промокод: {promo_code}")

    await callback.message.edit_text(
        "\n".join(preview),
        reply_markup=order_confirm_keyboard(""),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(OrderCallback.filter(F.action == "submit"))
async def order_submit(callback: CallbackQuery, state: FSMContext, session) -> None:
    """Создаёт заказ, уведомляет админа, запускает оплату."""
    data = await state.get_data()
    user = await catalog_service.get_or_create_user(session, callback.from_user.id)
    cart = await catalog_service.get_cart(session, user)
    if not cart.items:
        await callback.answer("Корзина пуста", show_alert=True)
        await state.clear()
        return

    source = user.last_source or "bot"
    order = await create_order_from_cart(
        session,
        user,
        cart,
        name=data.get("customer_name", ""),
        phone=data.get("phone", ""),
        address=data.get("address", ""),
        delivery_method=data.get("delivery_method", ""),
        payment_method=data.get("payment_method", ""),
        comment=data.get("comment", ""),
        discount=data.get("discount", 0),
        delivery_cost=data.get("delivery_cost", 0),
        promo_code=data.get("promo_code"),
        source=source,
    )
    await catalog_service.clear_cart(session, user)
    await state.update_data(order_id=order.id, order_number=order.number)
    await state.set_state(OrderState.PAYMENT)

    # Уведомление администратору
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    from bot.keyboards.factories import AdminCallback

    kb = InlineKeyboardBuilder()
    kb.button(text="👀 Открыть", callback_data=AdminCallback(action="order", order_id=order.id).pack())
    await notify_admins(callback.bot, f"🆕 <b>Новый заказ</b> {order.number}\n\n{render_order(order)}", kb.as_markup())
    await notify_manager_group(callback.bot, f"🆕 Заказ {order.number}\n\n{render_order(order)}")

    await callback.message.edit_text(
        f"✅ <b>Заказ {order.number} создан!</b>\n\n{render_order(order)}\n\n",
        parse_mode="HTML",
    )

    # Оплата
    method = data.get("payment_method")
    if method in ONLINE_PAYMENT:
        await proceed_to_payment(callback, order, state)
    elif method == PaymentMethod.AVITO.value:
        await callback.message.answer(
            "🤝 Заказ передан. Менеджер пришлёт ссылку на безопасную сделку на Авито.\n\n"
            "Статус можно отслеживать в разделе «Мои заказы»."
        )
        await state.clear()
    else:
        await callback.message.answer(
            "💸 Для оплаты переводом менеджер свяжется с вами и пришлёт реквизиты.\n\n"
            "Ожидайте подтверждение в чате."
        )
        await state.clear()
    await callback.answer()


async def proceed_to_payment(callback: CallbackQuery, order: Order, state: FSMContext) -> None:
    """Отправляет invoice для онлайн-оплаты."""
    from bot.services.payment import build_invoice, send_payment_invoice

    method = order.payment_method
    invoice = build_invoice(order, method or PaymentMethod.CARD.value)
    try:
        msg = await send_payment_invoice(callback.bot, callback.from_user.id, invoice)
        if msg is None and order.payment_method != PaymentMethod.TELEGRAM_STARS.value:
            await callback.message.answer(
                "💳 Онлайн-оплата временно недоступна. Мы создали заказ — менеджер пришлёт "
                "реквизиты для оплаты в ближайшее время."
            )
            await state.clear()
            return
        await state.set_state(OrderState.PAYMENT)
    except Exception:  # noqa: BLE001
        logger.exception("Ошибка отправки invoice")
        await callback.message.answer(
            "💳 Не удалось сформировать счёт. Менеджер свяжется с вами для оплаты."
        )
        await state.clear()


# ─────────────────────────────────────────────────────────────────────
# Заказ из Telegram Mini App (sendData)
# ─────────────────────────────────────────────────────────────────────
@router.message(F.web_app_data)
async def webapp_order(message: Message, state: FSMContext) -> None:
    """Принимает заказ из Mini App-витрины (web_app_data)."""
    await state.clear()
    from bot.services.webapp import process_webapp_order

    await process_webapp_order(message.bot, message, message.web_app_data.data)


# ─────────────────────────────────────────────────────────────────────
# Промокод
# ─────────────────────────────────────────────────────────────────────
@router.message(OrderState.PROMO)
async def apply_promo_code(message: Message, state: FSMContext, session) -> None:
    if not message.text:
        return
    code = message.text.strip()
    if code.lower() == "/отмена":
        await state.set_state(OrderState.CONFIRMATION)
        await message.answer("Промокод не применён.")
        return
    promo = await get_promo(session, code)
    if promo is None or not promo.is_valid:
        await message.answer("❌ Промокод не найден или неактивен. Попробуйте ещё раз:\n\n/отмена")
        return
    user = await catalog_service.get_or_create_user(session, message.from_user.id)
    cart = await catalog_service.get_cart(session, user)
    if cart.total_price < promo.min_order:
        await message.answer(f"❌ Промокод действует от {promo.min_order:,} ₽".replace(",", " "))
        return
    discount = promo.discount_for(cart.total_price)
    promo.used_count += 1
    await session.commit()
    await state.update_data(promo_code=promo.code, discount=discount)
    await state.set_state(OrderState.CONFIRMATION)
    await message.answer(
        f"✅ Промокод {promo.code} применён: −{discount:,} ₽".replace(",", " ") +
        "\nВернитесь к оформлению через корзину или меню."
    )
