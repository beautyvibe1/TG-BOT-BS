"""FSM-состояния для многошаговых сценариев."""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class OrderState(StatesGroup):
    """Сценарий оформления заказа."""

    CART = State()
    NAME = State()
    PHONE = State()
    DELIVERY_METHOD = State()
    ADDRESS = State()
    PAYMENT_METHOD = State()
    CONFIRMATION = State()
    PROMO = State()
    COMMENT = State()
    PAYMENT = State()
    DONE = State()


class ConsultationState(StatesGroup):
    """Сценарий консультации."""

    TOPIC = State()
    MESSAGE = State()
    CONTACT = State()


class AdminBroadcastState(StatesGroup):
    """Рассылка от имени админа."""

    TEXT = State()
    CONFIRM = State()


class AdminPromoState(StatesGroup):
    """Создание промокода."""

    CODE = State()
    TYPE = State()
    VALUE = State()
    MIN_ORDER = State()
    MAX_USES = State()
    CONFIRM = State()


class AdminProductState(StatesGroup):
    """Добавление/редактирование товара."""

    FIELD = State()
    VALUE = State()
