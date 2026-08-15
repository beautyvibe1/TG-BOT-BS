"""Синхронизация каталога: сайт ↔ бот ↔ канал."""

from __future__ import annotations

import logging

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models import Product
from bot.services import catalog

logger = logging.getLogger(__name__)


async def sync_catalog_from_db_to_json(db: AsyncSession) -> dict[str, list]:
    """Сверяет JSON-каталог с БД и возвращает изменения (added / updated / removed).

    Единый источник правды — bot/data/catalog.json, БД — производная витрина.
    Здесь реализован diff для последующей публикации новых постов в канал.
    """
    from sqlalchemy import select

    db_products = (await db.scalars(select(Product))).all()
    json_products = {p["slug"]: p for p in catalog.get_products()}

    added = []
    updated = []
    for slug, raw in json_products.items():
        existing = next((p for p in db_products if p.slug == slug), None)
        if existing is None:
            added.append(slug)
        else:
            if existing.price != raw.get("price") or existing.image_url != raw.get("image"):
                updated.append(slug)
    removed = [p.slug for p in db_products if p.slug not in json_products]
    return {"added": added, "updated": updated, "removed": removed}


async def publish_new_products(db: AsyncSession, bot: Bot) -> list[str]:
    """Публикует в канал посты о товарах, которых ещё нет в БД.

    Возвращает список опубликованных slug. Требует channel-модуль.
    """
    from channel.poster import post_product_to_channel

    changes = await sync_catalog_from_db_to_json(db)
    published: list[str] = []
    for slug in changes["added"]:
        ok = await post_product_to_channel(bot, slug)
        if ok:
            published.append(slug)
    return published
