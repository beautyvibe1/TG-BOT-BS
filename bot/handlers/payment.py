"""Хэндлеры оплаты: pre_checkout_query, successful_payment, pay-кнопка."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message, PreCheckoutQuery, SuccessfulPayment

from bot.keyboards.factories import OrderCallback
from bot.models import Order, PaymentStatus
from bot.services.notification import notify_admins
from bot.services.payment import confirm_pre_checkout, handle_successful_payment, parse_invoice_payload

logger = logging.getLogger(__name__)

router = Router(name="payment")


@router.pre_checkout_query()
async def on_pre_checkout(pre_checkout_query: PreCheckoutQuery) -> None:
    """Обязательно ответить < 10 секунд. Полностью async."""
    payload = pre_checkout_query.invoice_payload
    order_number = parse_invoice_payload(payload or "")
    if order_number is None:
        await confirm_pre_checkout(pre_checkout_query, ok=False, error="Некорректный счёт. Обратитесь к менеджеру.")
        return
    await confirm_pre_checkout(pre_checkout_query, ok=True)


@router.message(F.successful_payment)
async def on_successful_payment(message: Message, session) -> None:
    payment: SuccessfulPayment = message.successful_payment
    order_number = parse_invoice_payload(payment.invoice_payload or "")
    if order_number is None:
        await message.answer("Оплата получена, но не удалось найти заказ. Напишите менеджеру.")
        return

    from sqlalchemy import select

    order = await session.scalar(select(Order).where(Order.number == order_number))
    if order is None:
        await message.answer(f"Оплата получена за {order_number}. Мы свяжемся с вами.")
        return

    await handle_successful_payment(order, payment)
    await session.commit()

    total = f"{order.total:,}".replace(",", " ")
    await message.answer(
        f"✅ <b>Оплата получена!</b>\n\n"
        f"Заказ <b>{order.number}</b>\n"
        f"Сумма: <b>{total} {payment.currency}</b>\n\n"
        f"Мы приступили к обработке. Статус заказа — в разделе «📦 Мои заказы».\n"
        f"Спасибо за покупку! ✨",
        parse_mode="HTML",
    )
    await notify_admins(
        message.bot,
        f"💳 <b>Оплачен заказ {order.number}</b>\nСумма: {total} {payment.currency}\n"
        f"Чек TG: {payment.telegram_payment_charge_id}",
    )


@router.callback_query(OrderCallback.filter(F.action == "pay"))
async def pay_button(callback: CallbackQuery, callback_data: OrderCallback, session) -> None:
    """Кнопка «Оплатить» из карточки заказа."""
    from sqlalchemy import select

    order = await session.scalar(select(Order).where(Order.id == int(callback_data.value)))
    if order is None:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    if order.payment_status == PaymentStatus.SUCCEEDED.value:
        await callback.answer("Заказ уже оплачен", show_alert=True)
        return
    from bot.services.payment import build_invoice, send_payment_invoice

    method = order.payment_method or "card"
    invoice = build_invoice(order, method)
    try:
        await send_payment_invoice(callback.bot, callback.from_user.id, invoice)
    except Exception:  # noqa: BLE001
        logger.exception("Ошибка повторной оплаты")
        await callback.answer("Ошибка. Попробуйте позже.", show_alert=True)
    await callback.answer()
