# Competency System Backend

Технический README для backend-сервиса: стек, конфиг окружения, запуск через Docker и структура кода.

## Стек

- Python 3.12
- FastAPI + Uvicorn
- SQLAlchemy 2 + Alembic
- PostgreSQL
- Celery + Redis
- Airflow 2
- OpenAI-compatible LLM API (по умолчанию OpenRouter)
- Инструменты качества: pytest, mypy, ruff

## Быстрый запуск (Docker-only)

1. Создайте локальный конфиг:

```bash
cp .env.example .env
```

2. Заполните обязательные значения в `.env`:
- `API_KEY`
- `SECRET_KEY`
- `POSTGRES_PASSWORD`
- `REDIS_PASSWORD`
- `AIRFLOW__WEBSERVER__SECRET_KEY`
- `AIRFLOW__CORE__FERNET_KEY`
- `DOCKER_SOCKET` (путь к docker.sock в вашей среде, в том числе rootless)

3. Поднимите сервисы:

```bash
docker compose up -d --build
```

4. Проверка доступности:
- API docs: `http://localhost:1000/docs`
- Health: `http://localhost:1000/health`
- Airflow API/UI: `http://localhost:8080`

## Сервисы и порты

| Сервис              | Порт хоста | Назначение                               |
| ------------------- | ---------: | ---------------------------------------- |
| `api`               |     `1000` | HTTP API backend                         |
| `airflow-webserver` |     `8080` | Airflow UI/API                           |
| `postgres`          |     `1432` | PostgreSQL                               |
| `redis`             |     `1379` | Redis (broker/result backend для Celery) |

## Переменные окружения

Источник: `.env`. Шаблон и комментарии: `.env.example`.

### Application

| Переменная        | Что задаёт                 | Пример                                        |
| ----------------- | -------------------------- | --------------------------------------------- |
| `LOG_LEVEL`       | уровень логирования        | `INFO`                                        |
| `DEBUG`           | debug-режим приложения     | `false`                                       |
| `ALLOWED_ORIGINS` | CORS origins через запятую | `http://localhost:3000,http://127.0.0.1:3000` |

### Database (backend)

| Переменная | Что задаёт                     | Пример          |
| ---------- | ------------------------------ | --------------- |
| `DB_HOST`  | хост PostgreSQL для backend    | `postgres`      |
| `DB_PORT`  | порт PostgreSQL                | `5432`          |
| `DB_NAME`  | имя БД backend                 | `competency_db` |
| `DB_USER`  | пользователь БД backend        | `postgres`      |
| `DB_PASS`  | пароль пользователя БД backend | `password`      |

### LLM

| Переменная                        | Что задаёт                                        | Пример                         |
| --------------------------------- | ------------------------------------------------- | ------------------------------ |
| `API_KEY`                         | ключ LLM API                                      | `your-api-key`                 |
| `BASE_URL`                        | базовый URL LLM API                               | `https://openrouter.ai/api/v1` |
| `MODEL`                           | модель LLM                                        | `openai/gpt-oss-20b`           |
| `LLM_TIMEOUT_SECONDS`             | таймаут одного LLM-запроса                        | `30`                           |
| `LLM_RETRY_ATTEMPTS`              | число повторов LLM-запроса                        | `3`                            |
| `LLM_MAX_PARALLEL_REQUESTS`       | максимум параллельных запросов                    | `4`                            |
| `LLM_STAGE_TIMEOUT_SECONDS`       | таймаут этапа LLM пайплайна                       | `45`                           |
| `VACANCY_PROMPT_VERSION`          | версия промпта вакансии                           | `v1`                           |
| `TASK_PROMPT_VERSION`             | версия промпта задач                              | `v1`                           |
| `CODE_PROMPT_VERSION`             | версия промпта code-assessment                    | `v1`                           |
| `LLM_MAX_SUGGESTED_NEW_PER_STAGE` | лимит новых компетенций на этап                   | `5`                            |
| `LLM_REASONING_MAX_TOKENS`        | лимит reasoning токенов (`0` = без явного лимита) | `0`                            |
| `LLM_QUEUE_BACKEND`               | backend очереди LLM: `inmemory` или `celery`      | `celery`                       |

### Redis + Celery

| Переменная                         | Что задаёт                    | Пример     |
| ---------------------------------- | ----------------------------- | ---------- |
| `REDIS_HOST`                       | хост Redis                    | `redis`    |
| `REDIS_PORT`                       | порт Redis                    | `6379`     |
| `REDIS_PASSWORD`                   | пароль Redis                  | `password` |
| `CELERY_QUEUE_NAME`                | имя очереди                   | `llm_jobs` |
| `CELERY_RESULT_EXPIRES_SECONDS`    | TTL результатов задач         | `86400`    |
| `CELERY_RETRY_ATTEMPTS`            | число повторов задач          | `3`        |
| `CELERY_RETRY_BACKOFF_SECONDS`     | стартовая задержка backoff    | `2`        |
| `CELERY_RETRY_BACKOFF_MAX_SECONDS` | максимальная задержка backoff | `30`       |

### External Testing System

| Переменная                      | Что задаёт                           | Пример                  |
| ------------------------------- | ------------------------------------ | ----------------------- |
| `TESTING_SYSTEM_BASE_URL`       | URL внешней тестовой системы         | `http://localhost:9000` |
| `TESTING_SYSTEM_API_TOKEN`      | токен API внешней системы            | ``                      |
| `TESTING_SYSTEM_WEBHOOK_SECRET` | shared-secret для `X-Webhook-Secret` | `change-me`             |

### Airflow

| Переменная                            | Что задаёт                    | Пример                                                    |
| ------------------------------------- | ----------------------------- | --------------------------------------------------------- |
| `AIRFLOW_USERNAME`                    | логин Airflow                 | `admin`                                                   |
| `AIRFLOW_PASSWORD`                    | пароль Airflow                | `admin`                                                   |
| `AIRFLOW_IMAGE_NAME`                  | тег образа Airflow            | `competency-system/airflow:latest`                        |
| `AIRFLOW__CORE__EXECUTOR`             | executor Airflow              | `LocalExecutor`                                           |
| `AIRFLOW__CORE__DAGS_FOLDER`          | путь к DAG внутри контейнера  | `/app/src/competency_system/presentation/airflow/dags`    |
| `AIRFLOW__CORE__LOAD_EXAMPLES`        | включение demo DAG            | `False`                                                   |
| `AIRFLOW__LOGGING__BASE_LOG_FOLDER`   | папка логов Airflow           | `/opt/airflow/logs`                                       |
| `AIRFLOW__WEBSERVER__SECRET_KEY`      | webserver secret key          | `change-me`                                               |
| `AIRFLOW__CORE__FERNET_KEY`           | fernet key для шифрования     | `change-me`                                               |
| `AIRFLOW__DATABASE__SQL_ALCHEMY_CONN` | connection string metadata DB | `postgresql+psycopg2://airflow:password@postgres/airflow` |

### Auth and Bootstrap

| Переменная                    | Что задаёт                | Пример              |
| ----------------------------- | ------------------------- | ------------------- |
| `JWT_ALGORITHM`               | алгоритм подписи JWT      | `HS256`             |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | TTL access token (мин)    | `15`                |
| `REFRESH_TOKEN_EXPIRE_DAYS`   | TTL refresh token (дни)   | `7`                 |
| `SECRET_KEY`                  | секрет подписи токенов    | `change-me`         |
| `AUTH_COOKIE_SECURE`          | secure-флаг cookie        | `false`             |
| `AUTH_COOKIE_SAMESITE`        | same-site политика cookie | `lax`               |
| `BOOTSTRAP_ADMIN_EMAIL`       | email bootstrap-админа    | `admin@example.com` |
| `BOOTSTRAP_ADMIN_PASSWORD`    | пароль bootstrap-админа   | `change-me`         |

### Postgres container (system DB for Airflow)

| Переменная          | Что задаёт                                 | Пример     |
| ------------------- | ------------------------------------------ | ---------- |
| `POSTGRES_USER`     | системный пользователь postgres-контейнера | `airflow`  |
| `POSTGRES_DB`       | системная БД postgres-контейнера           | `airflow`  |
| `POSTGRES_PASSWORD` | пароль системного пользователя             | `password` |

### Docker socket

| Переменная      | Что задаёт                                          | Пример                       |
| --------------- | --------------------------------------------------- | ---------------------------- |
| `DOCKER_SOCKET` | путь к docker.sock на хосте для Airflow-контейнеров | `/run/user/1000/docker.sock` |

## Краткая структура проекта

```text
src/competency_system/
├── domain/            # сущности и бизнес-правила
├── application/       # use-cases, DTO, порты
├── infrastructure/    # БД, внешние интеграции, настройки
└── presentation/      # FastAPI и Airflow entrypoints
```

## Полезные команды

```bash
# пересобрать и поднять всё
docker compose up -d --build

# посмотреть статусы сервисов
docker compose ps

# посмотреть логи API
docker compose logs -f api
```
