"""Парсинг каталога с сайта → bot/data/catalog.json.

Источники (по приоритету):
  1. --local /path/to/site/src/data/products.ts — локальный клон репо сайта
  2. удалённый raw.githubusercontent.com (по умолчанию)

Использование:
    python -m scripts.parse_catalog [--local /path/to/products.ts]
    python -m scripts.parse_catalog --diff-only
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

from bot.config import BASE_DIR

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("parse_catalog")

DEFAULT_OUTPUT = BASE_DIR / "bot" / "data" / "catalog.json"


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    logger.info("Сохранено: %s (%d товаров)", path, len(data.get("products", [])))


async def main() -> int:
    parser = argparse.ArgumentParser(description="Парсер каталога Beauty Supply")
    parser.add_argument("--local", help="Путь к products.ts из локального клона сайта")
    parser.add_argument("--diff-only", action="store_true", help="Только показать diff без записи")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Путь к catalog.json")
    args = parser.parse_args()

    from channel.parser import build_catalog, diff_catalogs, parse_from_file, parse_from_remote

    if args.local:
        products = parse_from_file(args.local)
    else:
        print("Скачиваю products.ts с GitHub…")
        products = await parse_from_remote()

    new_catalog = build_catalog(products)

    output = Path(args.output)
    if output.exists():
        old_catalog = json.loads(output.read_text(encoding="utf-8"))
        diff = diff_catalogs(old_catalog, new_catalog)
        print(
            f"Diff: добавлено={len(diff['added'])} "
            f"изменено={len(diff['updated'])} удалено={len(diff['removed'])}"
        )
        for slug in diff["added"]:
            print(f"  + {slug}")
        for slug in diff["removed"]:
            print(f"  - {slug}")
        if args.diff_only:
            return 0
    else:
        print("Создаю новый каталог.")

    save_json(output, new_catalog)
    print(f"Готово: {len(products)} товаров.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
