"""Админ-панель: статистика, заказы, каталог, промокоды, рассылка, канал."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import get_settings
from bot.filters import IsAdmin
from bot.keyboards.factories import AdminCallback, MenuCallback
from bot.keyboards.inline import (
    admin_menu_keyboard,
    admin_order_keyboard,
    admin_orders_keyboard,
    admin_products_keyboard,
    admin_promos_keyboard,
    main_inline_menu,
)
from bot.models import Consultation, Order, OrderStatus, Promo, PromoType
from bot.services.order import render_order
from bot.states import AdminBroadcastState, AdminPromoState

logger = logging.getLogger(__name__)

router = Router(name="admin")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.message(Command("admin", "panel"))
async def admin_cmd(message: Message) -> None:
    await message.answer("🔐 <b>Админ-панель</b>", reply_markup=admin_menu_keyboard(), parse_mode="HTML")


@router.callback_query(AdminCallback.filter(F.action == "back"))
async def admin_back(callback: CallbackQuery) -> None:
    await callback.message.edit_text("🔐 <b>Админ-панель</b>", reply_markup=admin_menu_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(AdminCallback.filter(F.action == "stats"))
async def admin_stats(callback: CallbackQuery, session) -> None:
    from datetime import datetime, timedelta
    from sqlalchemy import func, select

    now = datetime.utcnow()
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    total_orders = int((await session.scalar(select(func.count(Order.id)))) or 0)
    total_revenue = int((await session.scalar(select(func.coalesce(func.sum(Order.total), 0)))) or 0)
    day_orders = int((await session.scalar(select(func.count(Order.id)).where(Order.created_at >= day_ago))) or 0)
    week_orders = int((await session.scalar(select(func.count(Order.id)).where(Order.created_at >= week_ago))) or 0)
    month_orders = int((await session.scalar(select(func.count(Order.id)).where(Order.created_at >= month_ago))) or 0)
    clients = int((await session.scalar(select(func.count()).select_from(__import__("bot.models", fromlist=["User"]).User))) or 0)
    unpaid = int((await session.scalar(select(func.count(Order.id)).where(Order.status == OrderStatus.NEW.value))) or 0)

    text = (
        "📊 <b>Статистика</b>\n\n"
        f"👥 Клиентов: <b>{clients}</b>\n"
        f"🛒 Всего заказов: <b>{total_orders}</b>\n"
        f"📅 За день: <b>{day_orders}</b>\n"
        f"📅 За неделю: <b>{week_orders}</b>\n"
        f"📅 За месяц: <b>{month_orders}</b>\n"
        f"⏳ В обработке: <b>{unpaid}</b>\n"
        f"💰 Выручка (всего): <b>{total_revenue:,} ₽</b>".replace(",", " ")
    )
    await callback.message.edit_text(text, reply_markup=admin_menu_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(AdminCallback.filter(F.action == "orders"))
async def admin_orders(callback: CallbackQuery, session) -> None:
    from sqlalchemy import select

    orders = (await session.scalars(select(Order).order_by(Order.created_at.desc()).limit(10))).all()
    if not orders:
        await callback.message.edit_text("📦 Заказов пока нет.", reply_markup=admin_menu_keyboard())
        await callback.answer()
        return
    await callback.message.edit_text("📦 <b>Последние заказы:</b>", reply_markup=admin_orders_keyboard(list(orders)), parse_mode="HTML")
    await callback.answer()


@router.callback_query(AdminCallback.filter(F.action == "order"))
async def admin_order_detail(callback: CallbackQuery, callback_data: AdminCallback, session) -> None:
    order = await session.get(Order, callback_data.order_id)
    if order is None:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    kb = admin_order_keyboard(order.id, order.status_enum)
    await callback.message.edit_text(render_order(order), reply_markup=kb, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(AdminCallback.filter(F.action == "set_status"))
async def admin_set_status(callback: CallbackQuery, callback_data: AdminCallback, session) -> None:
    order = await session.get(Order, callback_data.order_id)
    if order is None:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    old = order.status
    order.status = callback_data.value
    await session.commit()
    await callback.answer(f"Статус изменён: {old} → {callback_data.value}")
    # Уведомляем клиента
    try:
        await callback.bot.send_message(
            order.user.tg_id,
            f"🔔 <b>Статус заказа {order.number}</b>\n\n{OrderStatus(callback_data.value).label}",
            parse_mode="HTML",
        )
    except Exception:  # noqa: BLE001
        logger.exception("Не удалось уведомить клиента о статусе")
    await admin_order_detail(callback, callback_data, session)


@router.callback_query(AdminCallback.filter(F.action == "catalog"))
async def admin_catalog(callback: CallbackQuery) -> None:
    await callback.message.edit_text("📝 <b>Каталог</b> — выберите товар для редактирования:", reply_markup=admin_products_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(AdminCallback.filter(F.action == "product"))
async def admin_product(callback: CallbackQuery, callback_data: AdminCallback) -> None:
    from bot.services.catalog import get_product_by_id

    product = get_product_by_id(callback_data.product_id)
    if product is None:
        await callback.answer("Товар не найден")
        return
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.button(text="↕️ Наличие", callback_data=AdminCallback(action="toggle_avail", product_id=product["id"]).pack())
    builder.button(text="🔙", callback_data=AdminCallback(action="catalog").pack())
    builder.adjust(1)
    price = f"{product['price']:,}".replace(",", " ")
    avail = "✅" if product.get("available") else "❌"
    text = (
        f"<b>{product.get('ruName') or product['name']}</b>\n"
        f"{product['brand']}\n"
        f"Цена: {price} ₽\n"
        f"В наличии: {avail}\n\n"
        "Сейчас редактирование через JSON-каталог (bot/data/catalog.json)."
    )
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(AdminCallback.filter(F.action == "toggle_avail"))
async def admin_toggle_avail(callback: CallbackQuery, callback_data: AdminCallback, session) -> None:
    from bot.models import Product
    from sqlalchemy import select

    product = await session.scalar(select(Product).where(Product.external_id == callback_data.product_id))
    if product:
        product.available = not product.available
        await session.commit()
        await callback.answer("Обновлено")
    else:
        await callback.answer("Товар не в БД (запустите seed)")
    await admin_catalog(callback)


@router.callback_query(AdminCallback.filter(F.action == "product_add"))
async def admin_product_add(callback: CallbackQuery) -> None:
    await callback.message.answer(
        "📝 Добавление товара выполняется через единый каталог:\n\n"
        "1. Отредактируйте `bot/data/catalog.json`\n"
        "2. Запустите `python -m scripts.seed_db`\n\n"
        "Скрипт синхронизирует новые позиции в БД и канал.",
        parse_mode="Markdown",
    )
    await callback.answer()


# ─────────────────────────────────────────────────────────────────────
# Промокоды
# ─────────────────────────────────────────────────────────────────────
@router.callback_query(AdminCallback.filter(F.action == "promos"))
async def admin_promos(callback: CallbackQuery, session) -> None:
    from sqlalchemy import select

    promos = (await session.scalars(select(Promo).order_by(Promo.created_at.desc()).limit(10))).all()
    lines = ["🏷 <b>Промокоды</b>", ""]
    for promo in promos:
        lines.append(
            f"• <code>{promo.code}</code> — {promo.promo_type}={promo.value} "
            f"({promo.used_count}/{promo.max_uses or '∞'}) {'✅' if promo.is_valid else '⛔️'}"
        )
    lines.append("")
    await callback.message.edit_text("\n".join(lines), reply_markup=admin_promos_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(AdminCallback.filter(F.action == "promo_add"))
async def admin_promo_add(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminPromoState.CODE)
    await callback.message.answer("🏷 Введите код промокода (латиница, без пробелов):")
    await callback.answer()


@router.message(AdminPromoState.CODE)
async def promo_code(message: Message, state: FSMContext) -> None:
    code = message.text.strip().upper()
    if not code or " " in code:
        await message.answer("Некорректный код. Только латиница и цифры, без пробелов:")
        return
    await state.update_data(code=code)
    await state.set_state(AdminPromoState.TYPE)
    await message.answer("Тип скидки:\n1 — процент\n2 — фиксированная (₽)")


@router.message(AdminPromoState.TYPE)
async def promo_type(message: Message, state: FSMContext) -> None:
    choice = message.text.strip()
    if choice == "1":
        await state.update_data(promo_type=PromoType.PERCENT.value)
    elif choice == "2":
        await state.update_data(promo_type=PromoType.FIXED.value)
    else:
        await message.answer("Введите 1 (процент) или 2 (фиксированная):")
        return
    await state.set_state(AdminPromoState.VALUE)
    await message.answer("Величина скидки (для % — число 1–100):")


@router.message(AdminPromoState.VALUE)
async def promo_value(message: Message, state: FSMContext) -> None:
    try:
        value = int(message.text.strip())
    except ValueError:
        await message.answer("Введите целое число:")
        return
    data = await state.get_data()
    if data.get("promo_type") == PromoType.PERCENT.value and not (0 < value <= 100):
        await message.answer("Для процента укажите 1–100:")
        return
    await state.update_data(value=value)
    await state.set_state(AdminPromoState.MIN_ORDER)
    await message.answer("Минимальная сумма заказа (₽), 0 — без ограничений:")


@router.message(AdminPromoState.MIN_ORDER)
async def promo_min_order(message: Message, state: FSMContext) -> None:
    try:
        min_order = int(message.text.strip() or "0")
    except ValueError:
        await message.answer("Введите число:")
        return
    await state.update_data(min_order=min_order)
    await state.set_state(AdminPromoState.MAX_USES)
    await message.answer("Лимит использований (0 — безлимит):")


@router.message(AdminPromoState.MAX_USES)
async def promo_max_uses(message: Message, state: FSMContext) -> None:
    try:
        max_uses = int(message.text.strip() or "0")
    except ValueError:
        await message.answer("Введите число:")
        return
    await state.update_data(max_uses=max_uses if max_uses > 0 else None)
    data = await state.get_data()
    await message.answer(
        f"Подтвердите промокод:\n\n"
        f"Код: <b>{data['code']}</b>\n"
        f"Тип: {data['promo_type']} = {data['value']}\n"
        f"Мин. заказ: {data['min_order']} ₽\n"
        f"Лимит: {data['max_uses'] or '∞'}\n\n"
        "Отправьте <b>да</b> для создания.",
        parse_mode="HTML",
    )
    await state.set_state(AdminPromoState.CONFIRM)


@router.message(AdminPromoState.CONFIRM)
async def promo_confirm(message: Message, state: FSMContext, session) -> None:
    if not message.text or message.text.strip().lower() != "да":
        await state.clear()
        await message.answer("Отменено.")
        return
    data = await state.get_data()
    promo = Promo(
        code=data["code"],
        promo_type=data["promo_type"],
        value=data["value"],
        min_order=data["min_order"],
        max_uses=data["max_uses"],
    )
    session.add(promo)
    await session.commit()
    await state.clear()
    await message.answer(f"✅ Промокод <code>{promo.code}</code> создан!", parse_mode="HTML")


# ─────────────────────────────────────────────────────────────────────
# Рассылка
# ─────────────────────────────────────────────────────────────────────
@router.callback_query(AdminCallback.filter(F.action == "broadcast"))
async def admin_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminBroadcastState.TEXT)
    await callback.message.answer("📢 Введите текст рассылки для подписчиков бота:\n\n/отмена")
    await callback.answer()


@router.message(AdminBroadcastState.TEXT)
async def broadcast_text(message: Message, state: FSMContext) -> None:
    if message.text and message.text.strip().lower() == "/отмена":
        await state.clear()
        await message.answer("Рассылка отменена.")
        return
    text = message.text or message.caption or ""
    if not text:
        await message.answer("Введите текст рассылки:")
        return
    await state.update_data(text=text)
    await state.set_state(AdminBroadcastState.CONFIRM)
    await message.answer(
        f"📢 Отправить рассылку?\n\n{text}\n\nОтправьте <b>да</b> для запуска, <b>нет</b> — отмена.",
        parse_mode="HTML",
    )


@router.message(AdminBroadcastState.CONFIRM)
async def broadcast_confirm(message: Message, state: FSMContext, session) -> None:
    if not message.text or message.text.strip().lower() != "да":
        await state.clear()
        await message.answer("Рассылка отменена.")
        return
    data = await state.get_data()
    from sqlalchemy import select
    from bot.models import User

    users = (await session.scalars(select(User).where(User.is_subscribed == True))).all()  # noqa: E712
    sent = failed = 0
    for user in users:
        try:
            await message.bot.send_message(user.tg_id, data["text"])
            sent += 1
        except Exception:  # noqa: BLE001
            failed += 1
        # Throttling против flood-контроля
        await __import__("asyncio").sleep(0.05)
    await state.clear()
    await message.answer(f"📊 Рассылка завершена.\n✅ Отправлено: {sent}\n❌ Ошибок: {failed}")


# ─────────────────────────────────────────────────────────────────────
# Публикация в канал
# ─────────────────────────────────────────────────────────────────────
@router.callback_query(AdminCallback.filter(F.action == "channel_post"))
async def admin_channel_post(callback: CallbackQuery) -> None:
    from channel.poster import post_product_to_channel
    from bot.services.catalog import get_products

    products = get_products()
    sent = 0
    await callback.message.edit_text("📣 Публикую товары в канал…", parse_mode="HTML")
    for product in products[:5]:
        try:
            ok = await post_product_to_channel(callback.bot, product["slug"])
            sent += int(ok)
        except Exception:  # noqa: BLE001
            logger.exception("Ошибка поста %s", product["slug"])
    await callback.message.answer(f"📣 Опубликовано в канал: {sent} постов.")
    await callback.answer()


@router.callback_query(AdminCallback.filter(F.action == "consultations"))
async def admin_consultations(callback: CallbackQuery, session) -> None:
    from sqlalchemy import select

    consults = (await session.scalars(select(Consultation).order_by(Consultation.created_at.desc()).limit(10))).all()
    if not consults:
        await callback.message.edit_text("💬 Обращений пока нет.", reply_markup=admin_menu_keyboard())
        await callback.answer()
        return
    lines = ["💬 <b>Последние обращения</b>", ""]
    for c in consults:
        status = "🟢" if not c.answered else "⚪️"
        lines.append(f"{status} #{c.id} · {c.message[:40]}")
    await callback.message.edit_text("\n".join(lines), reply_markup=admin_menu_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(AdminCallback.filter(F.action == "settings"))
async def admin_settings(callback: CallbackQuery) -> None:
    settings = get_settings()
    text = (
        "⚙️ <b>Настройки</b>\n\n"
        f"Режим: <code>{settings.bot_mode}</code>\n"
        f"Канал: {settings.channel_id}\n"
        f"Каталог: <code>{settings.catalog_path}</code>\n"
        f"Платежи: {'вкл' if settings.payments_enabled else 'выкл'}\n\n"
        "Все настройки задаются через `.env`."
    )
    await callback.message.edit_text(text, reply_markup=admin_menu_keyboard(), parse_mode="Markdown")
    await callback.answer()
