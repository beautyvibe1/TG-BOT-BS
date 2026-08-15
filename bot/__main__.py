"""Точка входа бота: python -m bot.

Режимы:
  polling  — для разработки (BOT_MODE=polling)
  webhook  — для продакшена (BOT_MODE=webhook, WEBHOOK_URL)
"""

from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)


async def main() -> None:
    from bot.config import get_settings
    from bot.main import (
        create_bot,
        create_dispatcher,
        on_shutdown,
        on_startup,
        setup_logging,
    )

    setup_logging()
    settings = get_settings()

    bot = create_bot()
    dp = create_dispatcher()

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    try:
        if settings.bot_mode == "webhook":
            await _run_webhook(bot, dp, settings)
        else:
            await _run_polling(bot, dp)
    finally:
        await bot.session.close()


async def _run_polling(bot, dp) -> None:
    logger.info("Запуск в polling-режиме…")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


async def _run_webhook(bot, dp, settings) -> None:
    from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
    from aiohttp import web

    if not settings.webhook_url:
        raise RuntimeError("BOT_MODE=webhook требует WEBHOOK_URL")

    await bot.set_webhook(settings.webhook_url + settings.webhook_path)

    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=settings.webhook_path)
    setup_application(app, dp, bot=bot)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host=settings.webapp_host, port=settings.webhook_port)
    await site.start()
    logger.info("Webhook запущен на %s:%s%s", settings.webapp_host, settings.webhook_port, settings.webhook_path)
    await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен")
