"""Тесты сервисного слоя."""

from __future__ import annotations

from datetime import UTC

from sqlalchemy import select

from bot.models import Category, Product, Promo
from bot.services import catalog
from bot.services.cart import format_price, get_promo, render_cart


async def test_catalog_products(catalog):
    products = catalog.get_products()
    assert len(products) == 13
    assert {c["id"] for c in catalog.get_categories()} == {"care", "spf", "makeup"}


async def test_catalog_meta(catalog):
    meta = catalog.get_meta()
    assert meta["shop"] == "Beauty Supply MSK"
    assert "site_url" in meta


async def test_search_products(catalog):
    result = catalog.search_products("retinol")
    assert result, "Поиск по 'retinol' должен что-то найти"
    assert all("retinol" in (p["name"] + p.get("ruName", "")).lower() for p in result)


async def test_seed_db(db_session):
    count = await catalog.seed_database(db_session)
    assert count >= 13
    products = (await db_session.scalars(select(Product))).all()
    categories = (await db_session.scalars(select(Category))).all()
    assert len(products) == 13
    assert len(categories) == 3
    first = products[0]
    assert first.price > 0
    assert first.benefits_list  # преимущества распарсены


async def test_get_or_create_user_and_cart(db_session):
    user = await catalog.get_or_create_user(db_session, 111, username="anna", first_name="Анна")
    assert user.id is not None
    # Повторный вызов возвращает того же пользователя
    user2 = await catalog.get_or_create_user(db_session, 111)
    assert user2.id == user.id

    cart = await catalog.get_cart(db_session, user)
    assert cart is not None


async def test_add_to_cart_accumulates(db_session):
    user = await catalog.get_or_create_user(db_session, 222)
    await catalog.seed_database(db_session)
    product = (await db_session.scalars(select(Product))).first()

    await catalog.add_to_cart(db_session, user, product.id, 2)
    await catalog.add_to_cart(db_session, user, product.id, 1)
    cart = await catalog.get_cart(db_session, user)
    assert cart.total_items == 3
    assert cart.total_price == product.price * 3


async def test_clear_cart(db_session):
    user = await catalog.get_or_create_user(db_session, 333)
    await catalog.seed_database(db_session)
    product = (await db_session.scalars(select(Product))).first()
    await catalog.add_to_cart(db_session, user, product.id, 1)
    await catalog.clear_cart(db_session, user)
    cart = await catalog.get_cart(db_session, user)
    assert cart.total_items == 0


async def test_promo_percent(db_session):
    promo = Promo(code="BS10", promo_type="percent", value=10)
    db_session.add(promo)
    await db_session.commit()
    fetched = await get_promo(db_session, "bs10")
    assert fetched is not None
    assert fetched.is_valid
    assert fetched.discount_for(1000) == 100


async def test_promo_expired(db_session):
    from datetime import datetime, timedelta

    promo = Promo(
        code="OLD",
        promo_type="fixed",
        value=50,
        expires_at=datetime.now(UTC) - timedelta(days=1),
    )
    db_session.add(promo)
    await db_session.commit()
    assert promo.is_valid is False


async def test_format_price():
    assert format_price(11599) == "11 599 ₽"
    assert format_price(0) == "0 ₽"


async def test_render_empty_cart(db_session):
    from bot.models import Cart

    cart = Cart(user_id=1)
    text = render_cart(cart)
    assert "Корзина пуста" in text


async def test_create_order_from_cart(db_session):
    from bot.services.order import create_order_from_cart

    user = await catalog.get_or_create_user(db_session, 444, username="buyer")
    await catalog.seed_database(db_session)
    product = (await db_session.scalars(select(Product))).first()
    await catalog.add_to_cart(db_session, user, product.id, 2)
    cart = await catalog.get_cart(db_session, user)

    order = await create_order_from_cart(
        db_session,
        user,
        cart,
        name="Тест",
        phone="+7999",
        address="Москва",
        delivery_method="cdek",
        payment_method="card",
        discount=0,
        delivery_cost=350,
    )
    assert order.number.startswith("BS-")
    assert order.total == product.price * 2 + 350
    assert len(order.items) == 1
    assert order.items[0].quantity == 2
