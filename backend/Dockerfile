ARG PYTHON_VERSION=3.12
ARG APP_HOME=/app

# =============================================================================
# base - system runtime packages
# =============================================================================
FROM python:${PYTHON_VERSION}-slim-bookworm AS base

ARG APP_HOME
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    APP_HOME=${APP_HOME} \
    UV_PYTHON_DOWNLOADS=0 \
    UV_PROJECT_ENVIRONMENT=${APP_HOME}/.venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONPATH=${APP_HOME}/src \
    PATH="${APP_HOME}/.venv/bin:${PATH}"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR ${APP_HOME}

# =============================================================================
# builder
# =============================================================================
FROM base AS builder
COPY --from=ghcr.io/astral-sh/uv:0.11.3 /uv /uvx /bin/

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*


RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=.python-version,target=.python-version \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev


FROM builder AS api_builder
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=.python-version,target=.python-version \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev --group=api

FROM builder AS worker_builder
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=.python-version,target=.python-version \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev --group=worker

FROM builder AS airflow_builder
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=.python-version,target=.python-version \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev --group=airflow


# =============================================================================
# api
# =============================================================================

FROM base AS api

ARG APP_HOME
ENV PATH="${APP_HOME}/.venv-api/bin:${PATH}"

COPY --from=api_builder ${APP_HOME}/.venv ${APP_HOME}/.venv
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic
COPY src ./src

RUN useradd -m -u 1000 appuser \
    && chown -R appuser:appuser ${APP_HOME}

USER appuser
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "competency_system.presentation.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

# =============================================================================
# worker
# =============================================================================

FROM base AS worker

ARG APP_HOME
ENV PATH="${APP_HOME}/.venv-worker/bin:${PATH}" \
    C_FORCE_ROOT=0

COPY --from=worker_builder ${APP_HOME}/.venv ${APP_HOME}/.venv
COPY src ./src

RUN useradd -m -u 1000 appuser \
    && chown -R appuser:appuser ${APP_HOME}

USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD test -f /tmp/celery_heartbeat \
        && [ "$(( $(date +%s) - $(date +%s -r /tmp/celery_heartbeat) ))" -lt 60 ] \
    || exit 1

CMD ["celery", "-A", "competency_system.presentation.worker.celery_worker:celery_app", "worker", "--loglevel", "info", "--queues", "llm_jobs"]

# =============================================================================
# airflow
# =============================================================================
FROM base AS airflow

ARG APP_HOME
ENV PATH="${APP_HOME}/.venv-airflow/bin:${PATH}" \
    AIRFLOW_HOME=/opt/airflow \
    AIRFLOW__CORE__EXECUTOR=DockerExecutor \
    AIRFLOW__CORE__DAGS_FOLDER=${APP_HOME}/src/competency_system/presentation/airflow/dags \
    AIRFLOW__CORE__LOAD_EXAMPLES=False \
    AIRFLOW__LOGGING__BASE_LOG_FOLDER=/opt/airflow/logs

COPY --from=airflow_builder ${APP_HOME}/.venv ${APP_HOME}/.venv
COPY src ./src

RUN useradd -m -u 1000 appuser \
    && mkdir -p /opt/airflow/logs /opt/airflow/plugins \
    && chown -R appuser:appuser ${APP_HOME} /opt/airflow

USER appuser
EXPOSE 8080

CMD ["airflow", "webserver"]

# =============================================================================
# test
# =============================================================================
FROM builder AS test

ARG APP_HOME
ENV PATH="${APP_HOME}/.venv/bin:${PATH}"

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=.python-version,target=.python-version \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --all-groups

COPY alembic/ ${APP_HOME}/alembic/
COPY tests/ ${APP_HOME}/tests/
COPY src ./src

CMD ["pytest"]