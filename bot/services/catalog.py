"""Работа с каталогом: загрузка JSON (single source of truth) и синхронизация в БД."""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import BASE_DIR, get_settings
from bot.models import Cart, CartItem, Category, Product, User

logger = logging.getLogger(__name__)

CATALOG_PATH = get_settings().catalog_path


@lru_cache
def load_catalog(path: Path | None = None) -> dict[str, Any]:
    """Читает каталог из JSON. Результат кэшируется — вызывайте
    ``load_catalog.cache_clear()`` после обновления файла.
    """
    path = path or CATALOG_PATH
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def clear_catalog_cache() -> None:
    load_catalog.cache_clear()


# ─────────────────────────────────────────────────────────────────────
# Доступ к данным из JSON (используется ботом для мгновенной витрины)
# ─────────────────────────────────────────────────────────────────────
def get_meta() -> dict[str, Any]:
    return load_catalog()["$meta"]


def get_categories() -> list[dict[str, Any]]:
    return list(load_catalog()["categories"])


def get_products() -> list[dict[str, Any]]:
    return list(load_catalog()["products"])


def get_product_by_id(product_id: int) -> dict[str, Any] | None:
    for product in get_products():
        if product["id"] == product_id:
            return product
    return None


def get_product_by_slug(slug: str) -> dict[str, Any] | None:
    for product in get_products():
        if product["slug"] == slug:
            return product
    return None


def get_category_by_id(category_id: str) -> dict[str, Any] | None:
    for cat in get_categories():
        if cat["id"] == category_id:
            return cat
    return None


def search_products(query: str) -> list[dict[str, Any]]:
    """Поиск по названию, бренду и категории (без учёта регистра)."""
    q = query.strip().lower()
    if not q:
        return []
    result: list[dict[str, Any]] = []
    for product in get_products():
        haystack = " ".join(
            [
                product.get("name", ""),
                product.get("ruName", ""),
                product.get("brand", ""),
                product.get("line", ""),
            ]
        ).lower()
        if q in haystack:
            result.append(product)
    return result


def get_faqs() -> list[list[str]]:
    return list(load_catalog().get("faqs", []))


def get_delivery() -> dict[str, Any]:
    return load_catalog().get("delivery", {})


def get_promos() -> list[dict[str, Any]]:
    return list(load_catalog().get("promos", []))


def get_reviews() -> list[dict[str, Any]]:
    return list(load_catalog().get("reviews", []))


# ─────────────────────────────────────────────────────────────────────
# Синхронизация JSON → БД
# ─────────────────────────────────────────────────────────────────────
async def sync_categories(db: AsyncSession) -> dict[str, Category]:
    """Создаёт/обновляет категории из JSON. Возвращает slug→Category."""
    mapping: dict[str, Category] = {}
    for index, raw in enumerate(get_categories()):
        cat = await db.scalar(select(Category).where(Category.slug == raw["id"]))
        if cat is None:
            cat = Category(slug=raw["id"], name=raw["name"], emoji=raw.get("emoji"), position=index)
            db.add(cat)
        else:
            cat.name = raw["name"]
            cat.emoji = raw.get("emoji")
            cat.position = index
        mapping[raw["id"]] = cat
    return mapping


async def sync_products(db: AsyncSession, categories: dict[str, Category] | None = None) -> int:
    """Синхронизирует товары из JSON в БД. Возвращает число обновлённых/новых."""
    categories = categories or await sync_categories(db)
    changed = 0
    for raw in get_products():
        product = await db.scalar(select(Product).where(Product.slug == raw["slug"]))
        cat = categories.get(raw.get("category", ""))
        if product is None:
            product = Product(slug=raw["slug"])
            db.add(product)
            changed += 1
        product.external_id = raw.get("id")
        product.brand = raw.get("brand", "")
        product.line = raw.get("line")
        product.name = raw.get("name", "")
        product.ru_name = raw.get("ruName")
        product.category = cat
        product.price = raw.get("price", 0)
        product.price_numeric = float(raw.get("price", 0))
        product.volume = raw.get("volume")
        product.badge = raw.get("badge")
        product.summary = raw.get("summary")
        product.benefits = json.dumps(raw.get("benefits", []), ensure_ascii=False)
        product.image_url = raw.get("image")
        product.source_url = raw.get("source")
        product.available = raw.get("available", True)
        product.in_stock = raw.get("in_stock")
        changed += 1
    await db.flush()
    return changed


async def seed_database(db: AsyncSession) -> int:
    """Полная синхронизация каталога. Возвращает количество обработанных товаров."""
    await sync_categories(db)
    count = await sync_products(db)
    await db.commit()
    logger.info("Каталог синхронизирован: %d товаров обработано", count)
    return count


# ─────────────────────────────────────────────────────────────────────
# User helpers
# ─────────────────────────────────────────────────────────────────────
async def get_or_create_user(db: AsyncSession, tg_id: int, *, username: str | None = None,
                              first_name: str | None = None, last_name: str | None = None) -> User:
    user = await db.scalar(select(User).where(User.tg_id == tg_id))
    if user is None:
        user = User(tg_id=tg_id, username=username, first_name=first_name, last_name=last_name)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user


# ─────────────────────────────────────────────────────────────────────
# Cart helpers (в БД)
# ─────────────────────────────────────────────────────────────────────
async def get_cart(db: AsyncSession, user: User) -> Cart:
    from sqlalchemy.orm import selectinload

    cart = await db.scalar(
        select(Cart).where(Cart.user_id == user.id).options(selectinload(Cart.items))
    )
    if cart is None:
        cart = Cart(user_id=user.id)
        db.add(cart)
        await db.commit()
        await db.refresh(cart)
    return cart


async def add_to_cart(db: AsyncSession, user: User, product_id: int, quantity: int = 1) -> CartItem:
    """Добавляет товар в корзину (увеличивает количество при повторе)."""
    cart = await get_cart(db, user)
    item = await db.scalar(
        select(CartItem).where(CartItem.cart_id == cart.id, CartItem.product_id == product_id)
    )
    if item is None:
        item = CartItem(cart_id=cart.id, product_id=product_id, quantity=quantity)
        db.add(item)
    else:
        item.quantity += quantity
    await db.commit()
    await db.refresh(item)
    return item


async def update_cart_item(db: AsyncSession, item_id: int, quantity: int) -> CartItem | None:
    item = await db.get(CartItem, item_id)
    if item is None:
        return None
    if quantity <= 0:
        await db.delete(item)
    else:
        item.quantity = quantity
    await db.commit()
    return item if item.quantity else None


async def remove_cart_item(db: AsyncSession, item_id: int) -> None:
    item = await db.get(CartItem, item_id)
    if item is not None:
        await db.delete(item)
        await db.commit()


async def clear_cart(db: AsyncSession, user: User) -> None:
    cart = await get_cart(db, user)
    items = (
        await db.scalars(select(CartItem).where(CartItem.cart_id == cart.id))
    ).all()
    for item in items:
        await db.delete(item)
    await db.commit()
    db.expire(cart)  # чтобы items перечитались при следующем обращении
