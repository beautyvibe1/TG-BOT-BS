"""Конфигурация бота через Pydantic Settings (из .env).

Все секреты и настройки берутся только из переменных окружения.
Никаких секретов в коде.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Корень проекта (на уровень выше bot/)
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Безопасная обёртка над переменными окружения."""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ─── Telegram ────────────────────────────────────────────────
    bot_token: str = Field(..., min_length=20, description="Токен бота от @BotFather")
    channel_id: str = "@beautysupplymsk"
    channel_url: str = "https://t.me/beautysupplymsk"
    admin_ids: list[int] = Field(default_factory=list)
    manager_group_id: int | None = None
    bot_username: str = "BEAUTYSUPPLYMSKBOT"

    # ─── Website ─────────────────────────────────────────────────
    site_url: str = "https://beautysupplymsk.github.io/new/"
    site_catalog_url: str = "https://beautysupplymsk.github.io/new/#catalog"
    site_repo_url: str = "https://github.com/BEAUTYSUPPLYMSK/new"
    avito_url: str = "https://www.avito.ru/user/7d5cc17e554a6f4d901ec51bdd907f7b/profile"
    instagram_url: str = "https://instagram.com/beautysupplymsk"
    support_email: str = "support@beauty-supply.shop"

    # ─── Database / Redis ────────────────────────────────────────
    database_url: str = f"sqlite+aiosqlite:///{BASE_DIR / 'data' / 'bot.db'}"
    redis_url: str = "redis://localhost:6379/0"
    use_redis: bool = True

    # ─── Payments ────────────────────────────────────────────────
    payment_provider_token: str = ""
    yookassa_shop_id: str = ""
    yookassa_secret_key: str = ""
    payment_currency: str = "RUB"
    payments_enabled: bool = False

    # ─── Mini App ────────────────────────────────────────────────
    webapp_url: str = "https://beautyvibe1.github.io/TG-BOT-BS/webapp/"
    webapp_secret: str = ""  # при пустом — используется bot_token

    # ─── Channel autoposting ─────────────────────────────────────
    channel_posting_enabled: bool = True
    channel_post_times: list[str] = Field(default_factory=lambda: ["09:00", "14:00", "19:00"])
    timezone: str = "Europe/Moscow"

    # ─── Common ──────────────────────────────────────────────────
    debug: bool = False
    log_level: str = "INFO"
    bot_mode: Literal["polling", "webhook"] = "polling"
    webhook_url: str = ""
    webhook_path: str = "/webhook"
    webhook_port: int = 8080
    webapp_host: str = "0.0.0.0"

    # ─── Каталог ─────────────────────────────────────────────────
    catalog_path: Path = BASE_DIR / "bot" / "data" / "catalog.json"

    # ─── ─────────────────────────────────────────────────────────
    @field_validator("admin_ids", mode="before")
    @classmethod
    def _parse_admin_ids(cls, value: object) -> object:
        """Парсим admin_ids из строки json-массива, если пришла строка."""
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                cleaned = value.strip().strip("[]").replace(" ", "")
                if not cleaned:
                    return []
                return [int(part) for part in cleaned.split(",") if part]
        return value

    @field_validator("channel_post_times", mode="before")
    @classmethod
    def _parse_times(cls, value: object) -> object:
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass
            return [part.strip() for part in value.split(",") if part.strip()]
        return value

    @property
    def admins_set(self) -> set[int]:
        """Множество администраторов для быстрой проверки."""
        return set(self.admin_ids)

    def is_admin(self, user_id: int) -> bool:
        return user_id in self.admins_set

    @property
    def effective_webapp_secret(self) -> str:
        return self.webapp_secret or self.bot_token


@lru_cache
def get_settings() -> Settings:
    """Единственный экземпляр настроек на процесс (кэш)."""
    return Settings()


# Автосоздание директории для данных (sqlite)
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
