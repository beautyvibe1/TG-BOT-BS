"""CallbackData-фабрики для inline-клавиатур."""

from __future__ import annotations

from aiogram.filters.callback_data import CallbackData


class CatalogCallback(CallbackData, prefix="cat"):
    action: str          # show / page / product / back
    category: str = ""
    page: int = 1
    product_id: int = 0


class ProductCallback(CallbackData, prefix="prd"):
    action: str          # view / add / dec / remove / more / ask
    product_id: int = 0
    qty: int = 1


class CartCallback(CallbackData, prefix="crt"):
    action: str          # view / inc / dec / remove / checkout / clear / promo
    item_id: int = 0
    product_id: int = 0


class OrderCallback(CallbackData, prefix="ord"):
    action: str          # confirm / delivery / payment / submit / cancel / status
    value: str = ""


class AdminCallback(CallbackData, prefix="adm"):
    action: str
    value: str = ""
    order_id: int = 0
    product_id: int = 0


class MenuCallback(CallbackData, prefix="mnu"):
    action: str


class ConsultationCallback(CallbackData, prefix="csl"):
    action: str          # ask / faq / manager / topic / cancel
    value: str = ""
