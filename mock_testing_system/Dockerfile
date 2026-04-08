FROM ghcr.io/astral-sh/uv:python3.12-alpine AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /app

COPY pyproject.toml ./pyproject.toml
COPY uv.lock ./uv.lock
COPY .python-version ./.python-version

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"

RUN adduser -S -u 999 nonroot
WORKDIR /app

COPY --from=builder --chown=nonroot:nonroot /app/.venv /app/.venv
COPY --chown=nonroot:nonroot app.py /app/app.py

HEALTHCHECK --interval=30s --timeout=5s \
  CMD wget -q -O /dev/null http://127.0.0.1:9000/docs || exit 1

EXPOSE 9000
USER nonroot
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "9000"]
