# Beauty Supply MSK — Telegram-экосистема
# Многоступенчатая сборка: deps -> runtime

# ---- build stage ----
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml ./
COPY bot bot
COPY channel channel
COPY scripts scripts

# Установка зависимостей в отдельный слой
RUN pip install --upgrade pip && \
    pip install --no-cache-dir ".[dev]"

# ---- runtime stage ----
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Europe/Moscow

WORKDIR /app

# системные пакеты
RUN apt-get update && \
    apt-get install -y --no-install-recommends tzdata ca-certificates && \
    ln -snf /usr/share/zoneinfo/Europe/Moscow /etc/localtime && \
    echo Europe/Moscow > /etc/timezone && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY . .

# Точка входа — бот (polling). Для webhook задайте BOT_MODE=webhook.
CMD ["python", "-m", "bot"]
