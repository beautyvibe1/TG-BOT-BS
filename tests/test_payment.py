"""Тесты оплаты и безопасности Mini App."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from urllib.parse import urlencode

from bot.config import get_settings
from bot.models import Order, OrderItem, PaymentMethod
from bot.services.payment import build_invoice, parse_invoice_payload


def make_order() -> Order:
    order = Order(
        number="BS-TEST-00001",
        total=11599,
        items_total=11599,
        delivery_cost=0,
        discount=0,
        delivery_method="cdek",
    )
    order.items = [
        OrderItem(product_name="Крем", product_slug="krem", unit_price=11599, quantity=1)
    ]
    return order


def test_build_invoice_card():
    order = make_order()
    invoice = build_invoice(order, PaymentMethod.CARD.value)
    assert invoice.currency == "RUB"
    assert invoice.payload == "order:BS-TEST-00001"
    # Сумма в копейках
    assert invoice.prices[0].amount == order.total * 100


def test_build_invoice_stars():
    order = make_order()
    invoice = build_invoice(order, PaymentMethod.TELEGRAM_STARS.value)
    assert invoice.currency == "XTR"
    assert invoice.provider_token is None
    # Stars в целых единицах
    assert invoice.prices[0].amount == order.total


def test_parse_invoice_payload():
    assert parse_invoice_payload("order:BS-1") == "BS-1"
    assert parse_invoice_payload("other") is None


def _sign_init_data(secret: str, pairs: dict) -> str:
    data_check = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()) if k != "hash")
    secret_key = hmac.new(b"WebAppData", secret.encode(), hashlib.sha256).digest()
    h = hmac.new(secret_key, data_check.encode(), hashlib.sha256).hexdigest()
    pairs["hash"] = h
    return urlencode(pairs)


def test_validate_init_data_valid():
    from bot.services.webapp import validate_init_data

    settings = get_settings()
    pairs = {
        "auth_date": str(int(time.time())),
        "query_id": "AAHd",
        "user": json.dumps({"id": 123, "first_name": "A"}),
    }
    init_data = _sign_init_data(settings.effective_webapp_secret, pairs)
    result = validate_init_data(init_data)
    assert result is not None
    assert result["user"]["id"] == 123


def test_validate_init_data_tampered():
    from bot.services.webapp import validate_init_data

    settings = get_settings()
    pairs = {
        "auth_date": str(int(time.time())),
        "query_id": "AAHd",
        "user": json.dumps({"id": 123, "first_name": "A"}),
    }
    init_data = _sign_init_data(settings.effective_webapp_secret, pairs)
    # Подделываем данные после подписи (изменяем подписанное поле)
    tampered = init_data.replace("query_id=AAHd", "query_id=BBBB")
    assert validate_init_data(tampered) is None


def test_validate_init_data_empty():
    from bot.services.webapp import validate_init_data

    assert validate_init_data("") is None
