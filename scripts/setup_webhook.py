"""Настройка вебхука Telegram.

Устанавливает вебхук и удаляет pending-обновления.

Использование:
    python -m scripts.setup_webhook [--url https://example.com/webhook] [--delete]
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from bot.config import get_settings
from bot.main import create_bot


async def main() -> int:
    parser = argparse.ArgumentParser(description="Настройка вебхука")
    parser.add_argument("--url", help="Полный URL вебхука (включая путь)")
    parser.add_argument("--delete", action="store_true", help="Удалить вебхук")
    args = parser.parse_args()

    settings = get_settings()
    bot = create_bot()
    try:
        if args.delete:
            info = await bot.delete_webhook(drop_pending_updates=True)
            print(f"Вебхук удалён: {info}")
            return 0

        url = args.url or (settings.webhook_url + settings.webhook_path)
        info = await bot.set_webhook(url=url, drop_pending_updates=True, secret_token=None)
        print(f"Вебхук установлен: {url}\nОтвет: {info}")

        webhook = await bot.get_webhook_info()
        print(f"Текущий вебхук: {webhook.url}")
        return 0
    finally:
        await bot.session.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
