"""Регрессионные тесты для исправлений, сделанных в ходе аудита."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from bot.config import get_settings
from bot.models import Product
from bot.services import catalog
from bot.services.order import create_order_from_webapp, render_order


def test_resolved_channel_id_negative():
    """Числовой положительный ID канала должен приводиться к отрицательному."""
    settings = get_settings()
    assert settings.channel_id == "1003907669991"
    assert settings.resolved_channel_id == -1003907669991


async def test_add_to_cart_resolves_external_id(db_session):
    """add_to_cart должен работать по id каталога (external_id), а не по первичному ключу БД."""
    user = await catalog.get_or_create_user(db_session, 555)
    await catalog.seed_database(db_session)

    product = (await db_session.scalars(select(Product))).first()
    # Намеренно расходимся с первичным ключом
    product.external_id = 777
    await db_session.commit()

    await catalog.add_to_cart(db_session, user, 777, 1)
    cart = await catalog.get_cart(db_session, user)
    assert cart.total_items == 1
    assert cart.items[0].product_id == product.id
    assert cart.total_price == product.price


async def test_add_to_cart_unknown_product_raises(db_session):
    user = await catalog.get_or_create_user(db_session, 556)
    await catalog.seed_database(db_session)
    with pytest.raises(ValueError):
        await catalog.add_to_cart(db_session, user, 999_999, 1)


async def test_create_order_from_webapp(db_session):
    """Заказ из Mini App должен сохраняться в БД."""
    user = await catalog.get_or_create_user(db_session, 666, first_name="Аня")
    payload = {
        "source": "webapp",
        "customer_name": "Аня",
        "phone": "+79990000000",
        "address": "Москва",
        "delivery_method": "cdek",
        "comment": "",
        "items": [
            {"product_id": 1, "slug": "volu-lift-body", "name": "Лифтинг-комплекс для тела", "price": 7799, "qty": 2},
            {"product_id": 2, "slug": "volu-lift-face", "name": "Комплекс для плотности", "price": 11599, "qty": 1},
        ],
    }
    order = await create_order_from_webapp(db_session, user, payload)
    assert order.number.startswith("BS-")
    assert order.items_total == 7799 * 2 + 11599
    assert order.payment_method == "transfer"
    assert order.source == "webapp"
    assert len(order.items) == 2


def test_render_order_is_html():
    """render_order должен возвращать HTML с экранированием пользовательских данных."""
    from bot.models import Order, OrderItem

    order = Order(
        number="BS-1",
        items_total=100,
        delivery_cost=0,
        discount=0,
        total=100,
        customer_name="<Тест> & Co",
        phone="+7999",
        address="Москва",
        delivery_method="cdek",
        payment_method="card",
    )
    order.items = [OrderItem(product_name="Крем <b>", product_slug="krem", unit_price=100, quantity=1)]
    html = render_order(order)
    assert "&lt;Тест&gt; &amp; Co" in html
    assert "&lt;b&gt;" in html
    assert "<b>Заказ BS-1</b>" in html
