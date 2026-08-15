"""Регистрация всех хэндлеров бота."""

from __future__ import annotations

from aiogram import Dispatcher, Router

from . import admin, cart, catalog, common, consultation, order, payment, profile, start

main_router = Router(name="main")


def register_routers(dp: Dispatcher) -> None:
    """Подключает все роутеры к диспетчеру.

    Порядок важен: FSM-состояния и специфичные фильтры раньше catch-all.
    """
    dp.include_routers(
        admin.router,
        payment.router,
        order.router,
        cart.router,
        consultation.router,
        profile.router,
        catalog.router,
        start.router,
        common.router,
    )
