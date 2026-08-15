"""Логика оплаты: Telegram Payments API + ЮKassa + Telegram Stars + перевод."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from aiogram import Bot
from aiogram.types import LabeledPrice, PreCheckoutQuery, SuccessfulPayment

from bot.config import get_settings
from bot.models import Order, OrderItem, PaymentMethod, PaymentStatus

logger = logging.getLogger(__name__)


@dataclass
class InvoiceData:
    title: str
    description: str
    prices: list[LabeledPrice]
    currency: str
    payload: str
    provider_token: str | None
    need_name: bool = True
    need_phone_number: bool = True
    need_shipping_address: bool = False


def build_invoice(order: Order, payment_method: str = PaymentMethod.CARD.value) -> InvoiceData:
    """Формирует данные счёта для send_invoice().

    Telegram Stars (XTR): prices передаются в единицах Stars (1 Stars = 1 XTR),
    provider_token не нужен.
    """
    settings = get_settings()
    is_stars = payment_method == PaymentMethod.TELEGRAM_STARS.value

    if is_stars:
        currency = "XTR"
        provider_token = None
        # Telegram Stars принимает только цены в целых единицах
        prices = [LabeledPrice(label=f"Заказ {order.number}", amount=max(order.total, 1))]
    else:
        currency = settings.payment_currency
        provider_token = settings.payment_provider_token or None
        # В Telegram суммы в минимальных единицах (копейки)
        prices = [LabeledPrice(label=f"Заказ {order.number}", amount=order.total * 100)]

    item_lines = "\n".join(
        f"{item.product_name} ×{item.quantity}" for item in order.items
    )
    description = (
        f"Заказ {order.number}\n{item_lines}\n\n"
        f"Доставка: {order.delivery_method or '—'}"
    )[:1024]

    return InvoiceData(
        title=f"Beauty Supply — заказ {order.number}",
        description=description,
        prices=prices,
        currency=currency,
        payload=f"order:{order.number}",
        provider_token=provider_token,
    )


async def send_payment_invoice(bot: Bot, chat_id: int, invoice: InvoiceData) -> int | None:
    """Отправляет invoice и возвращает message_id."""
    settings = get_settings()
    if not settings.payments_enabled and invoice.currency != "XTR":
        logger.warning("Платежи отключены (PAYMENTS_ENABLED=false).")
        return None

    message = await bot.send_invoice(
        chat_id=chat_id,
        title=invoice.title,
        description=invoice.description,
        payload=invoice.payload,
        provider_token=invoice.provider_token,
        currency=invoice.currency,
        prices=invoice.prices,
        need_name=invoice.need_name,
        need_phone_number=invoice.need_phone_number,
        need_shipping_address=invoice.need_shipping_address,
    )
    return message.message_id


def parse_invoice_payload(payload: str) -> str | None:
    """Извлекает номер заказа из payload ('order:BS-...')."""
    if payload.startswith("order:"):
        return payload.removeprefix("order:")
    return None


async def confirm_pre_checkout(bot: Bot, query: PreCheckoutQuery, *, ok: bool, error: str = "") -> None:
    """Отвечает на pre_checkout_query (обязательно < 10 сек)."""
    if ok:
        await query.answer(ok=True)
    else:
        await query.answer(ok=False, error_message=error)


async def handle_successful_payment(order: Order, payment: SuccessfulPayment) -> Order:
    """Обновляет заказ после успешной оплаты."""
    order.payment_status = PaymentStatus.SUCCEEDED.value
    order.status = "paid"
    order.currency = payment.currency
    order.telegram_payment_charge_id = payment.telegram_payment_charge_id
    order.provider_payment_charge_id = payment.provider_payment_charge_id
    return order


# ─────────────────────────────────────────────────────────────────────
# ЮKassa (YooKassa) — прямое создание платежа (для webapp и админки)
# ─────────────────────────────────────────────────────────────────────
def create_yookassa_payment(order: Order, return_url: str) -> dict | None:
    """Создаёт платёж в ЮKassa. Возвращает словарь ответа API или None."""
    import yookassa

    settings = get_settings()
    if not settings.yookassa_shop_id or not settings.yookassa_secret_key:
        logger.warning("ЮKassa не сконфигурирована — пропуск платежа.")
        return None

    yookassa.Configuration.account_id = settings.yookassa_shop_id
    yookassa.Configuration.secret_key = settings.yookassa_secret_key

    try:
        return yookassa.Payment.create(
            {
                "amount": {"value": f"{order.total / 100:.2f}", "currency": "RUB"},
                "confirmation": {"type": "redirect", "return_url": return_url},
                "capture": True,
                "description": f"Заказ {order.number} Beauty Supply",
                "metadata": {"order_number": order.number},
            }
        )
    except Exception:  # noqa: BLE001
        logger.exception("Ошибка создания платежа ЮKassa")
        return None
