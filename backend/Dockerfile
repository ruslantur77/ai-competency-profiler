# =============================================================================
# Competency System - Dockerfile
# Minimal runtime for API and future worker stages.
# =============================================================================

ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim-bookworm AS base

ARG COMPETENCY_SYSTEM_HOME=/app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    COMPETENCY_SYSTEM_HOME=${COMPETENCY_SYSTEM_HOME} \
    PYTHONPATH=${COMPETENCY_SYSTEM_HOME}/src

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR ${COMPETENCY_SYSTEM_HOME}

# =============================================================================
# Dependencies stage
# =============================================================================
FROM base AS deps

COPY pyproject.toml README.md ${COMPETENCY_SYSTEM_HOME}/
COPY src/ ${COMPETENCY_SYSTEM_HOME}/src/
COPY alembic/ ${COMPETENCY_SYSTEM_HOME}/alembic/

RUN python -m venv ${COMPETENCY_SYSTEM_HOME}/.venv \
    && . ${COMPETENCY_SYSTEM_HOME}/.venv/bin/activate \
    && pip install --upgrade pip \
    && pip install -e ${COMPETENCY_SYSTEM_HOME}

# =============================================================================
# API stage
# =============================================================================
FROM base AS api

COPY --from=deps ${COMPETENCY_SYSTEM_HOME}/.venv ${COMPETENCY_SYSTEM_HOME}/.venv
ENV PATH="${COMPETENCY_SYSTEM_HOME}/.venv/bin:${PATH}"

COPY src/ ${COMPETENCY_SYSTEM_HOME}/src/
COPY alembic/ ${COMPETENCY_SYSTEM_HOME}/alembic/

RUN useradd -m -u 1000 appuser \
    && chown -R appuser:appuser ${COMPETENCY_SYSTEM_HOME}

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "competency_system.presentation.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

# =============================================================================
# Airflow stage
# =============================================================================
FROM api AS airflow

ENV AIRFLOW_HOME=/opt/airflow \
    AIRFLOW__CORE__EXECUTOR=DockerExecutor \
    AIRFLOW__CORE__DAGS_FOLDER=/app/src/competency_system/presentation/airflow/dags \
    AIRFLOW__CORE__LOAD_EXAMPLES=False \
    AIRFLOW__LOGGING__BASE_LOG_FOLDER=/opt/airflow/logs

HEALTHCHECK NONE
EXPOSE 8080

USER root
RUN mkdir -p /opt/airflow/logs /opt/airflow/plugins \
    && chown -R appuser:appuser /opt/airflow
USER appuser

CMD ["airflow", "webserver"]
