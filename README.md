# 💄 Beauty Supply MSK — Telegram-экосистема (канал + бот + Mini App)

Полноценная Telegram-экосистема для магазина косметики и товаров для красоты
**Beauty Supply MSK**: автопостинг товаров в канал, e-commerce бот (каталог,
корзина, заказы, оплата, консультации), Telegram Mini App-витрина и админ-панель.

> 🏷 **Beauty Supply** · MOSCOW · SINCE 2011 · Премиальная косметика из США.

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────┐     ┌──────────────────┐
│   АВИТО     │ ←→  │    САЙТ     │ ←→  │  TG КАНАЛ       │ ←→  │   TG БОТ         │
│ (готово)    │     │ (готово)    │     │  автопостинг    │     │ каталог/заказы/  │
└─────────────┘     └─────────────┘     └─────────────────┘     │ оплата/конс.     │
                          │  catalog.json (единый источник)     └──────────────────┘
                          └──────────→  БОТ + КАНАЛ + MINI APP
```

## ✨ Что умеет

**1. Telegram-канал — автопостинг**
- 🆕/📦 посты о товарах, 🔥 акции, 💡 beauty-советы, 📊 «Топ недели»
- HTML-оформление с эмодзи, фото товара, inline-кнопки **🛒 Заказать** (→ бот) и **🌐 На сайте**
- Расписание публикаций (APScheduler) с рандомизацией ±15 минут и защитой от flood-контроля

**2. Бот (aiogram 3.x)**
- `/start` → главное меню (ReplyKeyboard + inline)
- 🛍 Каталог по категориям, карточки товаров, пагинация, inline-поиск
- 🛒 Корзина (изменение количества, промокоды, очистка)
- 📦 Оформление заказа (FSM): имя → телефон → доставка → адрес → оплата → подтверждение
- 💳 Оплата: ЮKassa, СБП, Telegram Stars, перевод менеджеру, безопасная сделка на Авито
  (Telegram Payments API: `send_invoice`, `pre_checkout_query`, `successful_payment`)
- 💬 Консультации: FAQ-дерево + тикеты в группу менеджера с пересылкой ответов клиенту
- ⚙️ Настройки и профиль, 📦 история заказов со статусами
- 🔐 Админ-панель: статистика, управление заказами, промокоды, рассылки, публикации в канал

**3. Telegram Mini App (WebApp-витрина)**
- Адаптивный каталог в фирменном стиле, тёмная тема Telegram (`themeParams`)
- Корзина и оформление заказа прямо в Mini App
- Отправка заказа боту через `Telegram.WebApp.sendData()`
- Валидация `initData` на бэкенде (HMAC-SHA256)

**4. Безопасность**
- Секреты только в `.env`, валидация входящих данных (Pydantic)
- Throttling / anti-spam middleware, валидация WebApp initData
- `pre_checkout_query` отвечает < 10 сек (async), graceful shutdown, логирование (loguru)

## 📦 Технологии

| Слой | Стек |
|---|---|
| Бот | Python 3.12, **aiogram 3.x**, asyncio |
| ORM | SQLAlchemy 2 (async) + aioSQLite / asyncpg (PostgreSQL) |
| Миграции | Alembic |
| Кэш / FSM | Redis (aioredis), fallback — MemoryStorage |
| Планировщик | APScheduler |
| Валидация | Pydantic v2 |
| Платежи | YooKassa, Telegram Payments API, Telegram Stars |
| Витрина | HTML/CSS/JS, Telegram UI Kit |
| Инфраструктура | Docker + Docker Compose |

---

## 🚀 Быстрый старт

### 1. Клонирование и установка

```bash
git clone https://github.com/beautyvibe1/TG-BOT-BS.git
cd TG-BOT-BS

# Виртуальное окружение
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 2. Переменные окружения

```bash
cp .env.example .env
# Заполните .env своими значениями (токен, ADMIN_IDS, канал, платежи)
```

### 3. Парсинг каталога и заполнение БД

```bash
# Спарсить каталог с сайта → bot/data/catalog.json
python -m scripts.parse_catalog --local /path/to/site/src/data/products.ts
# или удалённо:
python -m scripts.parse_catalog

# Применить миграции БД
alembic upgrade head
# (либо автосоздание таблиц при первом старте)

# Наполнить БД из каталога
python -m scripts.seed_db
```

### 4. Запуск бота

```bash
# Режим разработки (polling)
python -m bot
```

> **Важно**: перед первым запуском создайте канал и добавьте бота админом.
> Для публикаций в канал у бота должны быть права на отправку сообщений.

### Docker

```bash
cp .env.example .env      # заполните
docker compose up -d --build
```

### Тесты

```bash
pytest -v
```

---

## 📝 Переменные окружения

См. полный список в [`.env.example`](.env.example). Ключевые:

| Переменная | Описание |
|---|---|
| `BOT_TOKEN` | Токен бота от @BotFather |
| `ADMIN_IDS` | JSON-массив Telegram ID администраторов |
| `CHANNEL_ID` | @username канала для автопостинга |
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/bot.db` или PostgreSQL |
| `REDIS_URL` | URL Redis (FSM/кэш) |
| `PAYMENT_PROVIDER_TOKEN` | Провайдер Telegram Payments |
| `YOOKASSA_SHOP_ID` / `YOOKASSA_SECRET_KEY` | ЮKassa |
| `WEBAPP_URL` | URL размещённой Mini App-витрины |
| `CHANNEL_POST_TIMES` | Расписание автопостинга (например `["09:00","14:00","19:00"]`) |
| `BOT_MODE` | `polling` (dev) или `webhook` (prod) |

---

## 🗂 Структура проекта

```
TG-BOT-BS/
├── README.md
├── .env.example
├── docker-compose.yml / Dockerfile
├── pyproject.toml / alembic.ini / alembic/
├── bot/
│   ├── __main__.py            # точка входа (python -m bot)
│   ├── main.py                # сборка Bot + Dispatcher
│   ├── config.py              # Pydantic Settings (.env)
│   ├── database.py            # async-движок/сессии
│   ├── filters.py             # фильтры (IsAdmin)
│   ├── handlers/              # start, catalog, cart, order, payment,
│   │                          # consultation, profile, admin, common
│   ├── keyboards/             # reply / inline / callback-фабрики
│   ├── middlewares/           # database, throttling, logging
│   ├── states/                # FSM-состояния (заказ, консультация, админка)
│   ├── models/                # SQLAlchemy: User, Product, Category, Cart,
│   │                          # Order, Promo, Consultation
│   ├── services/              # catalog, cart, order, payment, notification,
│   │                          # sync, webapp (initData)
│   ├── utils/                 # formatting, pagination
│   └── data/catalog.json      # ⭐ единый источник каталога
├── channel/
│   ├── parser.py              # парсинг каталога с сайта (+diff)
│   ├── templates.py           # шаблоны постов
│   ├── poster.py              # публикация в канал
│   └── scheduler.py           # расписание (APScheduler)
├── webapp/                    # Telegram Mini App (статическая витрина)
│   ├── index.html / css / js
│   └── assets/products/       # локальные фото товаров
├── scripts/                   # parse_catalog, seed_db, setup_webhook
└── tests/                     # pytest
```

---

## 🔄 Единый каталог (Single Source of Truth)

`bot/data/catalog.json` — единственный источник правды для бота, канала и Mini App.

| Компонент | Откуда берёт данные |
|---|---|
| Бот (витрина в БД) | `catalog.json` → `seed_db` |
| Канал (посты) | `catalog.json` (шаблоны + фото) |
| Mini App | `webapp/data/catalog.json` (сгенерирован из `bot/data/catalog.json`) |

Синхронизация при обновлении товара на сайте:
```bash
python -m scripts.parse_catalog --local /path/to/products.ts   # обновить catalog.json
python -m scripts.seed_db                                        # обновить БД
python -m bot                                                    # канал подхватит новые позиции
```
`scripts/parse_catalog.py --diff-only` покажет добавленные/изменённые/удалённые позиции.

---

## 🔌 Перелинковка экосистемы

- **Бот → Сайт**: кнопка «🌐 На сайте» в карточке товара
- **Бот → Авито**: кнопка «🤝 Avito» в разделе «О магазине»
- **Сайт → Бот**: deep-links `t.me/BOTUSERNAME?start=product_<slug>`, `preorder_usa`, `question`
- **Канал → Бот**: inline-кнопка «🛒 Заказать» с deep-link на конкретный товар
- **Канал → Сайт**: кнопка «🌐 На сайте»

**UTM/аналитика**: deep-links вида `?start=src_<источник>_<что-то>` записывают
источник перехода (avito/site/channel/webapp) в профиль пользователя и заказ.

---

## 💳 Оплата

- **ЮKassa (основной)** — российские карты, `PAYMENT_PROVIDER_TOKEN` из @BotFather
- **Telegram Stars** — мелкие цифровые позиции (валюта `XTR`)
- **Перевод менеджеру** — ручное подтверждение админом
- **Безопасная сделка на Авито** — ссылка на профиль

Для тестирования используйте тестовые ключи ЮKassa (тестовый магазин) и
`PAYMENTS_ENABLED=false` (эмуляция).

---

## 🚢 Деплой

**Вариант A — Docker (рекомендуется):**
```bash
docker compose up -d --build
```

**Вариант B — webhook (продакшен):**
```bash
# в .env
BOT_MODE=webhook
WEBHOOK_URL=https://ваш-домен.example
WEBHOOK_PATH=/webhook
WEBHOOK_PORT=8080
```
```bash
python -m bot                     # запускает aiohttp-сервер вебхука
# или
python -m scripts.setup_webhook --url https://ваш-домен.example/webhook
```

**Mini App:** соберите статику `webapp/` и разместите на GitHub Pages (как в
`beautyvibe1.github.io/TG-BOT-BS/webapp/`). В @BotFather в настройках бота
укажите **Menu button → WebApp → URL витрины**.

---

## 🧪 Тесты

```bash
pytest -v
```
Покрывают: каталог, корзину, промокоды, создание заказов, оплату (invoice),
валидацию initData (подпись/подделка), сборку хэндлеров и клавиатур.

---

## ⚠️ Безопасность

- Никогда не коммитьте `.env` (в `.gitignore`)
- Токены/ключи — только через переменные окружения
- Валидация всех входящих данных, `initData` (HMAC), throttling, логирование
- Ответ на `pre_checkout_query` — обязателен < 10 секунд (реализовано через async)

---

## 📄 Лицензия

Проект коммерческий, код принадлежит Beauty Supply MSK. Товарные знаки
принадлежат правообладателям (IMAGE Skincare, IMAGE MD, Charlotte Tilbury,
Hourglass). Изображения созданы на основе официальных product images.
