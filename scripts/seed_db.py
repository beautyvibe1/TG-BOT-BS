"""Заполнение БД из единого каталога (bot/data/catalog.json).

Синхронизирует категории и товары из JSON в БД.

Использование:
    python -m scripts.seed_db
"""

from __future__ import annotations

import asyncio
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("seed_db")


async def main() -> int:
    from bot.database import close_db, get_sessionmaker, init_db
    from bot.services import catalog

    await init_db()
    async with get_sessionmaker()() as session:
        count = await catalog.seed_database(session)
    await close_db()
    print(f"✅ Каталог синхронизирован: {count} товаров.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
