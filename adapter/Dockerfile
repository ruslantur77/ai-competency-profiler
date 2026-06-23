FROM python:3.11-slim

WORKDIR /app

# Устанавливаем uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Копируем зависимости
COPY pyproject.toml uv.lock* ./

# Устанавливаем зависимости (без dev)
RUN uv sync --frozen --no-dev

# Копируем исходники
COPY . .

# Порт адаптера
EXPOSE 8001

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8001/api/health').raise_for_status()"

# Запуск
CMD ["uv", "run", "main.py"]