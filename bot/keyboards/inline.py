"""InlineKeyboard: каталог, корзина, заказы, админка, консультации."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.config import get_settings
from bot.models import Order, OrderStatus
from bot.services.catalog import get_categories, get_products

from .factories import (
    AdminCallback,
    CartCallback,
    CatalogCallback,
    ConsultationCallback,
    MenuCallback,
    OrderCallback,
    ProductCallback,
)

PAGE_SIZE = 6

CATEGORY_EMOJI = {"care": "🧴", "spf": "☀️", "makeup": "💄", "all": "✨"}


# ─────────────────────────────────────────────────────────────────────
# Главное меню (inline поверх reply)
# ─────────────────────────────────────────────────────────────────────
def main_inline_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🛍 Каталог", callback_data=MenuCallback(action="catalog"))
    builder.button(text="🛒 Корзина", callback_data=MenuCallback(action="cart"))
    builder.button(text="📦 Мои заказы", callback_data=MenuCallback(action="orders"))
    builder.button(text="💬 Консультация", callback_data=MenuCallback(action="consult"))
    builder.button(text="🔥 Акции", callback_data=MenuCallback(action="promos"))
    builder.button(text="📍 Доставка", callback_data=MenuCallback(action="delivery"))
    builder.button(text="ℹ️ О магазине", callback_data=MenuCallback(action="about"))
    builder.button(text="🌐 Открыть витрину", url=get_settings().webapp_url)
    builder.adjust(2)
    return builder.as_markup()


# ─────────────────────────────────────────────────────────────────────
# Каталог
# ─────────────────────────────────────────────────────────────────────
def categories_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for cat in get_categories():
        builder.button(
            text=f"{cat['emoji']} {cat['name']} ({cat['count']})",
            callback_data=CatalogCallback(action="show", category=cat["id"]),
        )
    builder.button(text="✨ Все товары", callback_data=CatalogCallback(action="show", category="all"))
    builder.button(text="🔍 Поиск", switch_inline_query_current_chat="")
    builder.button(text="🔙 В меню", callback_data=MenuCallback(action="main"))
    builder.adjust(1)
    return builder.as_markup()


def products_keyboard(category: str, page: int = 1) -> InlineKeyboardMarkup:
    """Список товаров категории с пагинацией."""
    all_products = get_products()
    filtered = [p for p in all_products if p["category"] == category] if category != "all" else all_products

    total_pages = max((len(filtered) + PAGE_SIZE - 1) // PAGE_SIZE, 1)
    page = max(1, min(page, total_pages))
    start = (page - 1) * PAGE_SIZE
    chunk = filtered[start:start + PAGE_SIZE]

    builder = InlineKeyboardBuilder()
    for product in chunk:
        emoji = CATEGORY_EMOJI.get(category, "✨")
        label = product.get("ruName") or product["name"]
        builder.button(
            text=f"{emoji} {label} — {product['price']:,} ₽".replace(",", " "),
            callback_data=ProductCallback(action="view", product_id=product["id"]),
        )

    nav_row: list[InlineKeyboardButton] = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(
            text="⬅️", callback_data=CatalogCallback(action="page", category=category, page=page - 1).pack()
        ))
    nav_row.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton(
            text="➡️", callback_data=CatalogCallback(action="page", category=category, page=page + 1).pack()
        ))
    if nav_row:
        builder.row(*nav_row)
    builder.button(text="🔙 К категориям", callback_data=CatalogCallback(action="show", category=""))
    builder.button(text="🔍 Поиск", switch_inline_query_current_chat="")
    builder.adjust(1)
    return builder.as_markup()


def product_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """Карточка товара."""
    settings = get_settings()
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ В корзину", callback_data=ProductCallback(action="add", product_id=product_id, qty=1))
    builder.button(text="💬 Спросить", callback_data=ProductCallback(action="ask", product_id=product_id))
    builder.row(InlineKeyboardButton(
        text="🌐 На сайте",
        url=f"{settings.site_catalog_url}",
    ))
    builder.button(text="🔙 В список", callback_data=ProductCallback(action="list", product_id=product_id))
    builder.adjust(2)
    return builder.as_markup()


def product_qty_keyboard(product_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➖", callback_data=ProductCallback(action="dec", product_id=product_id))
    builder.button(text="❌", callback_data=ProductCallback(action="remove", product_id=product_id))
    builder.button(text="➕", callback_data=ProductCallback(action="add", product_id=product_id, qty=1))
    builder.button(text="🔙", callback_data=CatalogCallback(action="show", category="all"))
    builder.adjust(3)
    return builder.as_markup()


# ─────────────────────────────────────────────────────────────────────
# Корзина
# ─────────────────────────────────────────────────────────────────────
def cart_keyboard(items, *, can_checkout: bool = True) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for item in items:
        name = (item.product.ru_name or item.product.name)[:24]
        builder.button(
            text=f"{name} ×{item.quantity}",
            callback_data=CartCallback(action="view_item", item_id=item.id),
        )
    if can_checkout:
        builder.button(text="💳 Оформить заказ", callback_data=CartCallback(action="checkout"))
        builder.button(text="🎟 Промокод", callback_data=CartCallback(action="promo"))
    builder.button(text="🗑 Очистить", callback_data=CartCallback(action="clear"))
    builder.button(text="🛍 Продолжить покупки", callback_data=MenuCallback(action="catalog"))
    builder.adjust(1)
    return builder.as_markup()


def cart_item_actions(item_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➖", callback_data=CartCallback(action="dec", item_id=item_id))
    builder.button(text="➕", callback_data=CartCallback(action="inc", item_id=item_id))
    builder.button(text="🗑 Убрать", callback_data=CartCallback(action="remove", item_id=item_id))
    builder.button(text="🔙 В корзину", callback_data=CartCallback(action="view"))
    builder.adjust(3)
    return builder.as_markup()


# ─────────────────────────────────────────────────────────────────────
# Оформление заказа
# ─────────────────────────────────────────────────────────────────────
def delivery_methods_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for value, label in [
        ("moscow_courier", "🚗 Курьер по Москве"),
        ("cdek", "📦 СДЭК"),
        ("avito_delivery", "🤝 Avito Доставка"),
        ("self_pickup", "🏬 Самовывоз"),
    ]:
        builder.button(text=label, callback_data=OrderCallback(action="delivery", value=value))
    builder.adjust(1)
    return builder.as_markup()


def payment_methods_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Карта (ЮKassa)", callback_data=OrderCallback(action="payment", value="card"))
    builder.button(text="🏦 СБП", callback_data=OrderCallback(action="payment", value="sbp"))
    builder.button(text="💸 Перевод менеджеру", callback_data=OrderCallback(action="payment", value="transfer"))
    builder.button(text="🤝 Безопасная сделка на Авито", callback_data=OrderCallback(action="payment", value="avito"))
    builder.button(text="⭐ Telegram Stars", callback_data=OrderCallback(action="payment", value="telegram_stars"))
    builder.adjust(1)
    return builder.as_markup()


def order_confirm_keyboard(order_number: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data=OrderCallback(action="submit", value=order_number))
    builder.button(text="↩️ Вернуться", callback_data=CartCallback(action="view"))
    builder.adjust(1)
    return builder.as_markup()


# ─────────────────────────────────────────────────────────────────────
# Заказы
# ─────────────────────────────────────────────────────────────────────
def orders_keyboard(orders: list[Order]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for order in orders:
        builder.button(
            text=f"{order.number} · {order.status_enum.label}",
            callback_data=OrderCallback(action="status", value=str(order.id)),
        )
    builder.button(text="🔙 В меню", callback_data=MenuCallback(action="main"))
    builder.adjust(1)
    return builder.as_markup()


def order_status_keyboard(order_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Оплатить", callback_data=OrderCallback(action="pay", value=str(order_id)))
    builder.button(text="🔙 Мои заказы", callback_data=MenuCallback(action="orders"))
    builder.adjust(1)
    return builder.as_markup()


# ─────────────────────────────────────────────────────────────────────
# Консультации
# ─────────────────────────────────────────────────────────────────────
def consultation_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="❓ Частые вопросы", callback_data=ConsultationCallback(action="faq"))
    builder.button(text="💬 Написать менеджеру", callback_data=ConsultationCallback(action="manager"))
    builder.button(text="🔙 В меню", callback_data=MenuCallback(action="main"))
    builder.adjust(1)
    return builder.as_markup()


def faq_keyboard() -> InlineKeyboardMarkup:
    from bot.services.catalog import get_faqs

    builder = InlineKeyboardBuilder()
    for idx in range(len(get_faqs())):
        builder.button(text=f"Вопрос {idx + 1}", callback_data=ConsultationCallback(action="topic", value=str(idx)))
    builder.button(text="💬 Задать свой вопрос", callback_data=ConsultationCallback(action="manager"))
    builder.button(text="🔙", callback_data=ConsultationCallback(action="faq_back"))
    builder.adjust(2)
    return builder.as_markup()


def ask_manager_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙", callback_data=ConsultationCallback(action="faq_back"))
    builder.adjust(1)
    return builder.as_markup()


# ─────────────────────────────────────────────────────────────────────
# Промокоды / акции
# ─────────────────────────────────────────────────────────────────────
def promos_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🛍 В каталог", callback_data=MenuCallback(action="catalog"))
    builder.button(text="🔙 В меню", callback_data=MenuCallback(action="main"))
    builder.adjust(1)
    return builder.as_markup()


# ─────────────────────────────────────────────────────────────────────
# Админ-панель
# ─────────────────────────────────────────────────────────────────────
def admin_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Статистика", callback_data=AdminCallback(action="stats"))
    builder.button(text="📦 Заказы", callback_data=AdminCallback(action="orders"))
    builder.button(text="📝 Каталог", callback_data=AdminCallback(action="catalog"))
    builder.button(text="🏷 Промокоды", callback_data=AdminCallback(action="promos"))
    builder.button(text="📢 Рассылка", callback_data=AdminCallback(action="broadcast"))
    builder.button(text="📣 В канал", callback_data=AdminCallback(action="channel_post"))
    builder.button(text="💬 Консультации", callback_data=AdminCallback(action="consultations"))
    builder.button(text="⚙️ Настройки", callback_data=AdminCallback(action="settings"))
    builder.adjust(2)
    return builder.as_markup()


def admin_orders_keyboard(orders: list[Order]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for order in orders[:10]:
        builder.button(
            text=f"{order.number} · {order.status_enum.label}",
            callback_data=AdminCallback(action="order", order_id=order.id),
        )
    builder.button(text="🔙", callback_data=AdminCallback(action="back"))
    builder.adjust(1)
    return builder.as_markup()


def admin_order_keyboard(order_id: int, status: OrderStatus) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for new_status in [
        OrderStatus.CONFIRMED,
        OrderStatus.PAID,
        OrderStatus.PROCESSING,
        OrderStatus.SHIPPED,
        OrderStatus.DELIVERED,
        OrderStatus.CANCELLED,
    ]:
        if new_status != status:
            builder.button(
                text=f"→ {new_status.label}",
                callback_data=AdminCallback(action="set_status", order_id=order_id, value=new_status.value),
            )
    builder.button(text="🔙 Заказы", callback_data=AdminCallback(action="orders"))
    builder.adjust(2)
    return builder.as_markup()


def admin_products_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for product in get_products():
        builder.button(
            text=product.get("ruName") or product["name"],
            callback_data=AdminCallback(action="product", product_id=product["id"]),
        )
    builder.button(text="➕ Добавить", callback_data=AdminCallback(action="product_add"))
    builder.button(text="🔙", callback_data=AdminCallback(action="back"))
    builder.adjust(1)
    return builder.as_markup()


def admin_promos_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Создать промокод", callback_data=AdminCallback(action="promo_add"))
    builder.button(text="🔙", callback_data=AdminCallback(action="back"))
    builder.adjust(1)
    return builder.as_markup()
