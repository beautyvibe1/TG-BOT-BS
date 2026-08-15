"""Парсер каталога с сайта Beauty Supply MSK.

Извлекает товары из `src/data/products.ts` репозитория сайта
(https://github.com/BEAUTYSUPPLYMSK/new) и формирует структурированные данные,
совместимые с bot/data/catalog.json.

Источник данных: локальный клон репо или raw.githubusercontent.com.
Поддерживает diff — на выходе только изменённые/новые позиции.
"""

from __future__ import annotations

import ast
import json
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

RAW_PRODUCTS_URL = (
    "https://raw.githubusercontent.com/BEAUTYSUPPLYMSK/new/main/src/data/products.ts"
)
IMAGE_BASE = "https://beautysupplymsk.github.io/new/images/products/"

# Ключи схемы товара — для преобразования TS-объекта в JSON
SCHEMA_KEYS = {
    "id", "slug", "brand", "line", "name", "ruName", "category",
    "price", "volume", "badge", "image", "summary", "benefits", "source",
}

CATEGORY_NAMES = {"care": "Уход", "spf": "SPF-защита", "makeup": "Макияж"}
CATEGORY_EMOJI = {"care": "🧴", "spf": "☀️", "makeup": "💄"}


async def fetch_products_ts() -> str:
    """Скачивает products.ts с raw.githubusercontent.com."""
    import aiohttp

    async with aiohttp.ClientSession() as session:
        async with session.get(RAW_PRODUCTS_URL) as resp:
            resp.raise_for_status()
            return await resp.text()


def read_local_products_ts(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def _array_text(source: str) -> str:
    """Извлекает текст массива `products = [ ... ];`."""
    start = source.find("export const products")
    if start == -1:
        raise ValueError("Не найден блок products в products.ts")
    eq = source.find("=", start)
    if eq == -1:
        raise ValueError("Не найден оператор присваивания")
    bracket = source.find("[", eq)
    if bracket == -1:
        raise ValueError("Не найдена открывающая скобка массива")
    depth = 0
    for i in range(bracket, len(source)):
        if source[i] == "[":
            depth += 1
        elif source[i] == "]":
            depth -= 1
            if depth == 0:
                return source[bracket : i + 1]
    raise ValueError("Не закрыт массив products")


def _ts_to_python_literal(array_text: str) -> str:
    """Преобразует TS-массив объектов в python-литерал для ast.literal_eval."""
    # TS null/true/false -> Python
    text = re.sub(r"(?<![\w])null(?![\w])", "None", array_text)
    text = re.sub(r"(?<![\w])true(?![\w])", "True", text)
    text = re.sub(r"(?<![\w])false(?![\w])", "False", text)
    # Ключи-идентификаторы -> строки (только внутри объектов)
    # Безопасно: заменяем известные ключи схемы на `"key"`.
    def _quote(match: re.Match) -> str:
        return f'"{match.group(1)}":'

    text = re.sub(r"\b(" + "|".join(sorted(SCHEMA_KEYS, key=len, reverse=True)) + r")(\s*):", _quote, text)
    # Убираем хвостовые запятые (TS допускает, Python нет)
    text = re.sub(r",(\s*[\]}])", r"\1", text)
    return text


def parse_products_ts(source: str) -> list[dict[str, Any]]:
    """Разбирает products.ts в список словарей товаров."""
    arr_text = _array_text(source)
    py_literal = _ts_to_python_literal(arr_text)
    try:
        parsed = ast.literal_eval(py_literal)
    except (SyntaxError, ValueError) as exc:  # pragma: no cover
        logger.error("Ошибка разбора products.ts: %s", exc)
        raise
    products: list[dict[str, Any]] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        slug = str(item.get("slug", ""))
        image_file = str(item.get("image", "")).split("/")[-1]
        products.append(
            {
                "id": int(item["id"]),
                "slug": slug,
                "brand": str(item.get("brand", "")),
                "line": item.get("line"),
                "name": str(item.get("name", "")),
                "ruName": item.get("ruName"),
                "category": str(item.get("category", "")),
                "price": int(item.get("price", 0)),
                "volume": item.get("volume"),
                "badge": item.get("badge"),
                "image": IMAGE_BASE + image_file,
                "image_local": f"./images/products/{image_file}",
                "summary": item.get("summary"),
                "benefits": list(item.get("benefits", [])),
                "source": item.get("source"),
                "available": True,
                "in_stock": "В наличии",
            }
        )
    return products


def build_catalog(products: list[dict[str, Any]]) -> dict[str, Any]:
    """Собирает структуру catalog.json из списка товаров."""
    cat_counts: dict[str, int] = {}
    for p in products:
        cat_counts[p["category"]] = cat_counts.get(p["category"], 0) + 1
    categories = [
        {
            "id": cid,
            "name": CATEGORY_NAMES.get(cid, cid),
            "emoji": CATEGORY_EMOJI.get(cid, "✨"),
            "count": cat_counts.get(cid, 0),
        }
        for cid in ["care", "spf", "makeup"]
        if cid in cat_counts
    ]
    return {
        "$meta": {
            "shop": "Beauty Supply MSK",
            "source_repo": "https://github.com/BEAUTYSUPPLYMSK/new",
            "source_file": "src/data/products.ts",
        },
        "categories": categories,
        "products": products,
    }


def diff_catalogs(old: dict[str, Any], new: dict[str, Any]) -> dict[str, list[str]]:
    """Сравнивает два каталога и возвращает diff по slug."""
    old_map = {p["slug"]: p for p in old.get("products", [])}
    new_map = {p["slug"]: p for p in new.get("products", [])}
    added = [s for s in new_map if s not in old_map]
    updated = [
        s for s in new_map
        if s in old_map and old_map[s] != new_map[s]
    ]
    removed = [s for s in old_map if s not in new_map]
    return {"added": added, "updated": updated, "removed": removed}


async def parse_from_remote() -> list[dict[str, Any]]:
    source = await fetch_products_ts()
    return parse_products_ts(source)


def parse_from_file(path: str | Path) -> list[dict[str, Any]]:
    return parse_products_ts(read_local_products_ts(path))
