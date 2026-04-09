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
- `DB_PASS`
- `POSTGRES_PASSWORD`
- `REDIS_PASSWORD`
- `AIRFLOW__CORE__FERNET_KEY`
- `DOCKER_SOCKET` (путь к docker.sock в вашей среде, в том числе rootless)

3. Поднимите сервисы:

```bash
export DOCKER_GID=$(stat -c '%g' /var/run/docker.sock) docker compose up -d
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

Источник: `.env`. Источник истины для списка и комментариев переменных: `.env.example`.

### Application Variables

Переменные, читаемые приложением напрямую через `Settings` (`src/competency_system/infrastructure/settings.py`).

| Переменная                         | Required                               | Пример                                        | Consumer     |
| ---------------------------------- | -------------------------------------- | --------------------------------------------- | ------------ |
| `LOG_LEVEL`                        | optional                               | `INFO`                                        | app          |
| `DEBUG`                            | optional                               | `false`                                       | app          |
| `ENVIRONMENT`                      | optional                               | `local`                                       | app          |
| `ALLOWED_ORIGINS`                  | optional                               | `http://localhost:3000,http://127.0.0.1:3000` | app          |
| `DB_HOST`                          | required                               | `postgres`                                    | app          |
| `DB_PORT`                          | required                               | `5432`                                        | app          |
| `DB_NAME`                          | required                               | `competency_db`                               | app          |
| `DB_USER`                          | required                               | `postgres`                                    | app          |
| `DB_PASS`                          | required                               | `password`                                    | app          |
| `API_KEY`                          | required                               | `your-api-key`                                | app          |
| `BASE_URL`                         | optional                               | `https://openrouter.ai/api/v1`                | app          |
| `MODEL`                            | optional                               | `openai/gpt-oss-20b`                          | app          |
| `LLM_TIMEOUT_SECONDS`              | optional                               | `30`                                          | app          |
| `LLM_RETRY_ATTEMPTS`               | optional                               | `3`                                           | app          |
| `LLM_MAX_PARALLEL_REQUESTS`        | optional                               | `4`                                           | app          |
| `LLM_STAGE_TIMEOUT_SECONDS`        | optional                               | `45`                                          | app          |
| `VACANCY_PROMPT_VERSION`           | optional                               | `v1`                                          | app          |
| `TASK_PROMPT_VERSION`              | optional                               | `v1`                                          | app          |
| `CODE_PROMPT_VERSION`              | optional                               | `v1`                                          | app          |
| `LLM_MAX_SUGGESTED_NEW_PER_STAGE`  | optional                               | `5`                                           | app          |
| `LLM_REASONING_MAX_TOKENS`         | optional                               | `0`                                           | app          |
| `LLM_QUEUE_BACKEND`                | optional                               | `celery`                                      | app          |
| `REDIS_HOST`                       | required if `LLM_QUEUE_BACKEND=celery` | `redis`                                       | app          |
| `REDIS_PORT`                       | required if `LLM_QUEUE_BACKEND=celery` | `6379`                                        | app          |
| `REDIS_PASSWORD`                   | required if `LLM_QUEUE_BACKEND=celery` | `password`                                    | app + redis  |
| `CELERY_QUEUE_NAME`                | optional                               | `llm_jobs`                                    | app + worker |
| `CELERY_RESULT_EXPIRES_SECONDS`    | optional                               | `86400`                                       | app          |
| `CELERY_RETRY_ATTEMPTS`            | optional                               | `3`                                           | app          |
| `CELERY_RETRY_BACKOFF_SECONDS`     | optional                               | `2`                                           | app          |
| `CELERY_RETRY_BACKOFF_MAX_SECONDS` | optional                               | `30`                                          | app          |
| `TESTING_SYSTEM_BASE_URL`          | optional                               | `http://localhost:9000`                       | app          |
| `TESTING_SYSTEM_API_TOKEN`         | optional                               | ``                                            | app          |
| `TESTING_SYSTEM_WEBHOOK_SECRET`    | optional                               | `change-me`                                   | app          |
| `JWT_ALGORITHM`                    | optional                               | `HS256`                                       | app          |
| `ACCESS_TOKEN_EXPIRE_MINUTES`      | optional                               | `15`                                          | app          |
| `REFRESH_TOKEN_EXPIRE_DAYS`        | optional                               | `7`                                           | app          |
| `SECRET_KEY`                       | required                               | `change-me`                                   | app          |
| `AUTH_COOKIE_SECURE`               | optional                               | `false`                                       | app          |
| `AUTH_COOKIE_SAMESITE`             | optional                               | `lax`                                         | app          |
| `BOOTSTRAP_ADMIN_EMAIL`            | optional                               | `admin@example.com`                           | app          |
| `BOOTSTRAP_ADMIN_PASSWORD`         | optional                               | `change-me`                                   | app          |

### Runtime / Airflow / Infrastructure Variables

Переменные, которые не читаются `Settings` приложения, но используются docker-compose, Airflow и контейнерами.

| Переменная                                      | Required               | Пример                                                    | Consumer                 |
| ----------------------------------------------- | ---------------------- | --------------------------------------------------------- | ------------------------ |
| `AIRFLOW_IMAGE_NAME`                            | optional               | `competency-system/airflow:latest`                        | docker-compose image tag |
| `TASK_SYNC_IMAGE`                               | optional               | `competency-system/api:latest`                            | task_sync DockerOperator |
| `AIRFLOW_DOCKER_NETWORK`                        | required for task_sync | `backend_default`                                         | task_sync DockerOperator |
| `AIRFLOW__CORE__EXECUTOR`                       | required for airflow   | `LocalExecutor`                                           | airflow                  |
| `AIRFLOW__CORE__PARALLELISM`                    | optional               | `1`                                                       | airflow                  |
| `AIRFLOW__CORE__MAX_ACTIVE_TASKS_PER_DAG`       | optional               | `1`                                                       | airflow                  |
| `AIRFLOW__CORE__MAX_ACTIVE_RUNS_PER_DAG`        | optional               | `1`                                                       | airflow                  |
| `AIRFLOW__CORE__DAGS_FOLDER`                    | required for airflow   | `/app/src/competency_system/presentation/airflow/dags`    | airflow                  |
| `AIRFLOW__CORE__LOAD_EXAMPLES`                  | optional               | `False`                                                   | airflow                  |
| `AIRFLOW__SCHEDULER__PARSING_PROCESSES`         | optional               | `1`                                                       | airflow                  |
| `AIRFLOW__SCHEDULER__MIN_FILE_PROCESS_INTERVAL` | optional               | `30`                                                      | airflow                  |
| `AIRFLOW__LOGGING__BASE_LOG_FOLDER`             | optional               | `/opt/airflow/logs`                                       | airflow                  |
| `AIRFLOW__CORE__FERNET_KEY`                     | required               | `change-me`                                               | airflow                  |
| `AIRFLOW__DATABASE__SQL_ALCHEMY_CONN`           | required               | `postgresql+psycopg2://airflow:password@postgres/airflow` | airflow                  |
| `AIRFLOW__WEBSERVER__BASE_URL`                  | optional               | `http://example.com/airflow`                              | airflow                  |
| `AIRFLOW__API_AUTH__JWT_SECRET`                 | required               | `secret`                                                  | airflow api auth         |
| `AIRFLOW__API_AUTH__JWT_ISSUER`                 | optional               | `airflow`                                                 | airflow api auth         |
| `AIRFLOW__API__SECRET_KEY`                      | required               | `secret`                                                  | airflow api              |
| `AIRFLOW__API__BASE_URL`                        | required               | `http://airflow-webserver:8080`                           | airflow scheduler        |
| `CELERY_WORKER_CONCURRENCY`                     | optional               | `2`                                                       | celery worker command    |
| `CELERY_MAX_TASKS_PER_CHILD`                    | optional               | `100`                                                     | celery worker command    |
| `CELERY_WORKER_EXTRA_FLAGS`                     | optional               | `--without-gossip --without-mingle --without-heartbeat`   | celery worker command    |
| `POSTGRES_USER`                                 | required               | `airflow`                                                 | postgres container init  |
| `POSTGRES_DB`                                   | required               | `airflow`                                                 | postgres container init  |
| `POSTGRES_PASSWORD`                             | required               | `password`                                                | postgres container init  |
| `DOCKER_SOCKET`                                 | required               | `/run/user/1000/docker.sock`                              | airflow container mount  |

### Рассинхроны и решения (2026-04-08)

- В README были переменные `AIRFLOW_USERNAME`, `AIRFLOW_PASSWORD`, `AIRFLOW__WEBSERVER__SECRET_KEY`, но они не используются в текущем коде/compose; удалены из документации.
- В `.env.example` была `AIRFLOW__WEBSERVER__BASE_URL`, а в README ожидалась `AIRFLOW__WEBSERVER__SECRET_KEY`; README приведён к `AIRFLOW__WEBSERVER__BASE_URL`.
- В README отсутствовали runtime-переменные Airflow/Celery (`AIRFLOW__API_*`, `AIRFLOW__SCHEDULER_*`, `AIRFLOW__CORE__PARALLELISM`, `CELERY_WORKER_*`); добавлены.
- В `docker-compose.yml` используется `AIRFLOW_IMAGE_NAME`; переменная добавлена в `.env.example` и отражена в README.

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

## Airflow pipeline

В текущей конфигурации в Airflow оставлен только один DAG:

- `task_sync` (расписание: `@hourly`, оператор: `DockerOperator`).

Как работает запуск:

1. Airflow scheduler запускает DAG раз в час.
2. `DockerOperator` поднимает отдельный backend-контейнер (`TASK_SYNC_IMAGE`).
3. В контейнере запускается CLI-раннер `task_sync_runner`, который вызывает `SyncTasksUseCase` напрямую.
4. Период берётся из `data_interval_start/data_interval_end` (UTC), либо переопределяется через `dag_run.conf`.
5. Для каждой синхронизированной задачи ставится LLM job `TASK_MAPPING` в очередь (обычно Celery).

## Контракт синка задач

Синк задач выполняется через:

`POST /api/v1/tasks/sync`

С обязательным JSON body:

```json
{
  "start": "2026-04-01T00:00:00Z",
  "end": "2026-04-02T00:00:00Z"
}
```

Требования к периоду:
- оба поля обязательны;
- только UTC (ISO-8601, суффикс `Z`);
- интервал задаётся как `[start, end)`;
- `end` должен быть строго больше `start`.

Ручной запуск Airflow DAG `task_sync`:

- `dag_run.conf.start` и `dag_run.conf.end` опциональны;
- если не переданы, используются границы часового `data interval` самого Airflow.
