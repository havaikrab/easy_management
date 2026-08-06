FROM python:3.13-slim

WORKDIR /app

# 1. Системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 2. Создаем папки для статики
RUN mkdir -p /app/staticfiles

# 3. Устанавливаем Poetry
RUN pip install --no-cache-dir poetry

# 4. Копируем ТОЛЬКО файлы зависимостей
COPY pyproject.toml poetry.lock ./

# 5. Устанавливаем зависимости без создания виртуального окружения
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --no-root

# 6. Копируем ВЕСЬ код после установки зависимостей
COPY . .

# 7. Пробрасываем порты
EXPOSE 8000
