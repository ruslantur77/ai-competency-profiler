"""Seed test competency ontology.

Revision ID: 0005_seed_test_competency_ontology
Revises: 0004_mvp_hardening_and_reliability
Create Date: 2026-03-30 13:25:00
"""

from __future__ import annotations

from uuid import UUID

import sqlalchemy as sa

from alembic import op

revision = "0005_seed_test_competency_ontology"
down_revision = "0004_mvp_hardening_and_reliability"
branch_labels = None
depends_on = None


CATEGORY_IDS = {
    "backend_dev": UUID("2d95b3f8-fb4f-4e9f-9bc3-bd1b0f370101"),
    "data_storage": UUID("2d95b3f8-fb4f-4e9f-9bc3-bd1b0f370102"),
    "infrastructure": UUID("2d95b3f8-fb4f-4e9f-9bc3-bd1b0f370103"),
    "engineering_practices": UUID("2d95b3f8-fb4f-4e9f-9bc3-bd1b0f370104"),
}

COMPETENCY_IDS = {
    "api_design": UUID("3f08ed8b-fd8f-4e58-a913-5600e6a10101"),
    "python_backend": UUID("3f08ed8b-fd8f-4e58-a913-5600e6a10102"),
    "api_security": UUID("3f08ed8b-fd8f-4e58-a913-5600e6a10103"),
    "sql_modeling": UUID("3f08ed8b-fd8f-4e58-a913-5600e6a10104"),
    "db_performance": UUID("3f08ed8b-fd8f-4e58-a913-5600e6a10105"),
    "cache_queues": UUID("3f08ed8b-fd8f-4e58-a913-5600e6a10106"),
    "containers_cicd": UUID("3f08ed8b-fd8f-4e58-a913-5600e6a10107"),
    "observability": UUID("3f08ed8b-fd8f-4e58-a913-5600e6a10108"),
    "cloud_networking": UUID("3f08ed8b-fd8f-4e58-a913-5600e6a10109"),
    "testing": UUID("3f08ed8b-fd8f-4e58-a913-5600e6a1010a"),
    "architecture": UUID("3f08ed8b-fd8f-4e58-a913-5600e6a1010b"),
    "team_process": UUID("3f08ed8b-fd8f-4e58-a913-5600e6a1010c"),
}

SUB_COMPETENCY_IDS = {
    "api_rest": UUID("6f4f96ba-9343-42a1-b0cf-d31d86020101"),
    "api_versioning": UUID("6f4f96ba-9343-42a1-b0cf-d31d86020102"),
    "api_errors": UUID("6f4f96ba-9343-42a1-b0cf-d31d86020103"),
    "python_asyncio": UUID("6f4f96ba-9343-42a1-b0cf-d31d86020104"),
    "python_fastapi": UUID("6f4f96ba-9343-42a1-b0cf-d31d86020105"),
    "python_background_jobs": UUID("6f4f96ba-9343-42a1-b0cf-d31d86020106"),
    "security_authn": UUID("6f4f96ba-9343-42a1-b0cf-d31d86020107"),
    "security_authz": UUID("6f4f96ba-9343-42a1-b0cf-d31d86020108"),
    "security_secrets": UUID("6f4f96ba-9343-42a1-b0cf-d31d86020109"),
    "sql_normalization": UUID("6f4f96ba-9343-42a1-b0cf-d31d8602010a"),
    "sql_migrations": UUID("6f4f96ba-9343-42a1-b0cf-d31d8602010b"),
    "sql_transactions": UUID("6f4f96ba-9343-42a1-b0cf-d31d8602010c"),
    "db_indexes": UUID("6f4f96ba-9343-42a1-b0cf-d31d8602010d"),
    "db_explain": UUID("6f4f96ba-9343-42a1-b0cf-d31d8602010e"),
    "db_pooling": UUID("6f4f96ba-9343-42a1-b0cf-d31d8602010f"),
    "cache_redis": UUID("6f4f96ba-9343-42a1-b0cf-d31d86020110"),
    "queue_rabbit_kafka": UUID("6f4f96ba-9343-42a1-b0cf-d31d86020111"),
    "idempotency_retries": UUID("6f4f96ba-9343-42a1-b0cf-d31d86020112"),
    "docker": UUID("6f4f96ba-9343-42a1-b0cf-d31d86020113"),
    "cicd_pipelines": UUID("6f4f96ba-9343-42a1-b0cf-d31d86020114"),
    "deploy_strategy": UUID("6f4f96ba-9343-42a1-b0cf-d31d86020115"),
    "logs": UUID("6f4f96ba-9343-42a1-b0cf-d31d86020116"),
    "metrics": UUID("6f4f96ba-9343-42a1-b0cf-d31d86020117"),
    "incident_response": UUID("6f4f96ba-9343-42a1-b0cf-d31d86020118"),
    "cloud_basics": UUID("6f4f96ba-9343-42a1-b0cf-d31d86020119"),
    "network_basics": UUID("6f4f96ba-9343-42a1-b0cf-d31d8602011a"),
    "config_management": UUID("6f4f96ba-9343-42a1-b0cf-d31d8602011b"),
    "unit_tests": UUID("6f4f96ba-9343-42a1-b0cf-d31d8602011c"),
    "integration_tests": UUID("6f4f96ba-9343-42a1-b0cf-d31d8602011d"),
    "contract_tests": UUID("6f4f96ba-9343-42a1-b0cf-d31d8602011e"),
    "ddd_boundaries": UUID("6f4f96ba-9343-42a1-b0cf-d31d8602011f"),
    "clean_architecture": UUID("6f4f96ba-9343-42a1-b0cf-d31d86020120"),
    "scalability": UUID("6f4f96ba-9343-42a1-b0cf-d31d86020121"),
    "code_review": UUID("6f4f96ba-9343-42a1-b0cf-d31d86020122"),
    "task_decomposition": UUID("6f4f96ba-9343-42a1-b0cf-d31d86020123"),
    "documentation": UUID("6f4f96ba-9343-42a1-b0cf-d31d86020124"),
}


def upgrade() -> None:
    categories_table = sa.table(
        "categories",
        sa.column("id", sa.UUID(as_uuid=True)),
        sa.column("name", sa.String(length=100)),
        sa.column("description", sa.String(length=500)),
        sa.column("emoji", sa.String(length=10)),
    )
    competencies_table = sa.table(
        "competencies",
        sa.column("id", sa.UUID(as_uuid=True)),
        sa.column("category_id", sa.UUID(as_uuid=True)),
        sa.column("name", sa.String(length=100)),
        sa.column("description", sa.String(length=500)),
        sa.column("is_required", sa.Boolean()),
    )
    sub_competencies_table = sa.table(
        "sub_competencies",
        sa.column("id", sa.UUID(as_uuid=True)),
        sa.column("competency_id", sa.UUID(as_uuid=True)),
        sa.column("name", sa.String(length=100)),
        sa.column("description", sa.String(length=500)),
        sa.column("target_level", sa.Integer()),
        sa.column("weight", sa.Float()),
    )

    op.bulk_insert(
        categories_table,
        [
            {
                "id": CATEGORY_IDS["backend_dev"],
                "name": "Backend-разработка",
                "description": "Разработка прикладной серверной логики и API.",
                "emoji": "🧩",
            },
            {
                "id": CATEGORY_IDS["data_storage"],
                "name": "Данные и хранение",
                "description": "Реляционные БД, кэширование и надежность хранения.",
                "emoji": "🗄️",
            },
            {
                "id": CATEGORY_IDS["infrastructure"],
                "name": "Инфраструктура и эксплуатация",
                "description": "Доставка, мониторинг и эксплуатация сервисов.",
                "emoji": "🚀",
            },
            {
                "id": CATEGORY_IDS["engineering_practices"],
                "name": "Инженерные практики",
                "description": "Качество кода, тестирование и командные процессы.",
                "emoji": "⚙️",
            },
        ],
    )

    op.bulk_insert(
        competencies_table,
        [
            {
                "id": COMPETENCY_IDS["api_design"],
                "category_id": CATEGORY_IDS["backend_dev"],
                "name": "Проектирование API",
                "description": "Контракты API, совместимость и стабильное поведение.",
                "is_required": True,
            },
            {
                "id": COMPETENCY_IDS["python_backend"],
                "category_id": CATEGORY_IDS["backend_dev"],
                "name": "Python backend",
                "description": "Разработка сервисов на Python и веб-фреймворках.",
                "is_required": True,
            },
            {
                "id": COMPETENCY_IDS["api_security"],
                "category_id": CATEGORY_IDS["backend_dev"],
                "name": "Безопасность API",
                "description": "Аутентификация, авторизация и защита данных.",
                "is_required": True,
            },
            {
                "id": COMPETENCY_IDS["sql_modeling"],
                "category_id": CATEGORY_IDS["data_storage"],
                "name": "SQL и моделирование данных",
                "description": "Проектирование схем и контроль целостности данных.",
                "is_required": True,
            },
            {
                "id": COMPETENCY_IDS["db_performance"],
                "category_id": CATEGORY_IDS["data_storage"],
                "name": "Производительность БД",
                "description": "Оптимизация запросов и работа БД под нагрузкой.",
                "is_required": True,
            },
            {
                "id": COMPETENCY_IDS["cache_queues"],
                "category_id": CATEGORY_IDS["data_storage"],
                "name": "Кэш и очереди",
                "description": "Redis, очереди сообщений и асинхронные процессы.",
                "is_required": False,
            },
            {
                "id": COMPETENCY_IDS["containers_cicd"],
                "category_id": CATEGORY_IDS["infrastructure"],
                "name": "Контейнеризация и CI/CD",
                "description": "Сборка, доставка и безопасный деплой сервисов.",
                "is_required": True,
            },
            {
                "id": COMPETENCY_IDS["observability"],
                "category_id": CATEGORY_IDS["infrastructure"],
                "name": "Наблюдаемость",
                "description": "Логи, метрики, алерты и операционная диагностика.",
                "is_required": True,
            },
            {
                "id": COMPETENCY_IDS["cloud_networking"],
                "category_id": CATEGORY_IDS["infrastructure"],
                "name": "Облака и сеть",
                "description": "Базовые cloud-сервисы, сеть и конфигурация окружений.",
                "is_required": False,
            },
            {
                "id": COMPETENCY_IDS["testing"],
                "category_id": CATEGORY_IDS["engineering_practices"],
                "name": "Тестирование",
                "description": "Пирамида тестов и контроль регрессий.",
                "is_required": True,
            },
            {
                "id": COMPETENCY_IDS["architecture"],
                "category_id": CATEGORY_IDS["engineering_practices"],
                "name": "Архитектура приложения",
                "description": "Декомпозиция системы, границы модулей и рост нагрузки.",
                "is_required": True,
            },
            {
                "id": COMPETENCY_IDS["team_process"],
                "category_id": CATEGORY_IDS["engineering_practices"],
                "name": "Командная разработка",
                "description": "Code review, процессы команды и рабочая коммуникация.",
                "is_required": False,
            },
        ],
    )

    op.bulk_insert(
        sub_competencies_table,
        [
            {
                "id": SUB_COMPETENCY_IDS["api_rest"],
                "competency_id": COMPETENCY_IDS["api_design"],
                "name": "REST-эндпоинты и ресурсы",
                "description": "Маршруты, методы и структура API-ресурсов.",
                "target_level": 3,
                "weight": 1.0,
            },
            {
                "id": SUB_COMPETENCY_IDS["api_versioning"],
                "competency_id": COMPETENCY_IDS["api_design"],
                "name": "Версионирование API",
                "description": "Эволюция контрактов без поломки клиентов.",
                "target_level": 2,
                "weight": 0.8,
            },
            {
                "id": SUB_COMPETENCY_IDS["api_errors"],
                "competency_id": COMPETENCY_IDS["api_design"],
                "name": "Валидация и ошибки",
                "description": "Единый формат ошибок и строгая проверка входа.",
                "target_level": 3,
                "weight": 1.0,
            },
            {
                "id": SUB_COMPETENCY_IDS["python_asyncio"],
                "competency_id": COMPETENCY_IDS["python_backend"],
                "name": "Async Python",
                "description": "Event loop, async/await и работа с I/O-bound задачами.",
                "target_level": 3,
                "weight": 0.9,
            },
            {
                "id": SUB_COMPETENCY_IDS["python_fastapi"],
                "competency_id": COMPETENCY_IDS["python_backend"],
                "name": "FastAPI/ASGI стек",
                "description": "Роутинг, DI, middleware и работа со схемами данных.",
                "target_level": 3,
                "weight": 1.0,
            },
            {
                "id": SUB_COMPETENCY_IDS["python_background_jobs"],
                "competency_id": COMPETENCY_IDS["python_backend"],
                "name": "Фоновые задачи",
                "description": "Оркестрация jobs, ретраи и отказоустойчивая обработка.",
                "target_level": 2,
                "weight": 0.7,
            },
            {
                "id": SUB_COMPETENCY_IDS["security_authn"],
                "competency_id": COMPETENCY_IDS["api_security"],
                "name": "Аутентификация",
                "description": "JWT/сессии, refresh flow и lifecycle токенов.",
                "target_level": 3,
                "weight": 1.0,
            },
            {
                "id": SUB_COMPETENCY_IDS["security_authz"],
                "competency_id": COMPETENCY_IDS["api_security"],
                "name": "Авторизация",
                "description": "RBAC/ABAC и проверки прав на уровне endpoint/use case.",
                "target_level": 3,
                "weight": 1.0,
            },
            {
                "id": SUB_COMPETENCY_IDS["security_secrets"],
                "competency_id": COMPETENCY_IDS["api_security"],
                "name": "Управление секретами",
                "description": "Хранение, ротация секретов и security-практики.",
                "target_level": 2,
                "weight": 0.8,
            },
            {
                "id": SUB_COMPETENCY_IDS["sql_normalization"],
                "competency_id": COMPETENCY_IDS["sql_modeling"],
                "name": "Нормализация и связи",
                "description": "Проектирование таблиц, ключей и отношений.",
                "target_level": 3,
                "weight": 1.0,
            },
            {
                "id": SUB_COMPETENCY_IDS["sql_migrations"],
                "competency_id": COMPETENCY_IDS["sql_modeling"],
                "name": "Миграции схемы",
                "description": "Безопасные изменения схемы и обратимая эволюция БД.",
                "target_level": 3,
                "weight": 1.0,
            },
            {
                "id": SUB_COMPETENCY_IDS["sql_transactions"],
                "competency_id": COMPETENCY_IDS["sql_modeling"],
                "name": "Транзакции и изоляция",
                "description": "Уровни изоляции, блокировки и консистентность записи.",
                "target_level": 2,
                "weight": 0.9,
            },
            {
                "id": SUB_COMPETENCY_IDS["db_indexes"],
                "competency_id": COMPETENCY_IDS["db_performance"],
                "name": "Индексы",
                "description": "Подбор индексов под профиль запросов.",
                "target_level": 3,
                "weight": 0.9,
            },
            {
                "id": SUB_COMPETENCY_IDS["db_explain"],
                "competency_id": COMPETENCY_IDS["db_performance"],
                "name": "Планы выполнения",
                "description": "Чтение EXPLAIN/ANALYZE и устранение узких мест.",
                "target_level": 3,
                "weight": 0.9,
            },
            {
                "id": SUB_COMPETENCY_IDS["db_pooling"],
                "competency_id": COMPETENCY_IDS["db_performance"],
                "name": "Пулы соединений",
                "description": "Настройка pool size, timeouts и лимитов.",
                "target_level": 2,
                "weight": 0.8,
            },
            {
                "id": SUB_COMPETENCY_IDS["cache_redis"],
                "competency_id": COMPETENCY_IDS["cache_queues"],
                "name": "Redis-кэширование",
                "description": "Стратегии кеша, TTL и инвалидация.",
                "target_level": 2,
                "weight": 0.7,
            },
            {
                "id": SUB_COMPETENCY_IDS["queue_rabbit_kafka"],
                "competency_id": COMPETENCY_IDS["cache_queues"],
                "name": "Очереди сообщений",
                "description": "Брокеры сообщений, consumer-groups и доставка событий.",
                "target_level": 2,
                "weight": 0.8,
            },
            {
                "id": SUB_COMPETENCY_IDS["idempotency_retries"],
                "competency_id": COMPETENCY_IDS["cache_queues"],
                "name": "Идемпотентность и ретраи",
                "description": "Повторная обработка задач без дублирования эффектов.",
                "target_level": 2,
                "weight": 0.8,
            },
            {
                "id": SUB_COMPETENCY_IDS["docker"],
                "competency_id": COMPETENCY_IDS["containers_cicd"],
                "name": "Docker",
                "description": "Docker-образы: сборка, оптимизация и безопасность.",
                "target_level": 3,
                "weight": 0.9,
            },
            {
                "id": SUB_COMPETENCY_IDS["cicd_pipelines"],
                "competency_id": COMPETENCY_IDS["containers_cicd"],
                "name": "CI/CD pipelines",
                "description": "Автоматизация тестов, сборки и выката в окружения.",
                "target_level": 3,
                "weight": 1.0,
            },
            {
                "id": SUB_COMPETENCY_IDS["deploy_strategy"],
                "competency_id": COMPETENCY_IDS["containers_cicd"],
                "name": "Стратегии деплоя",
                "description": "Blue/green, rolling update и безопасный rollback.",
                "target_level": 2,
                "weight": 0.8,
            },
            {
                "id": SUB_COMPETENCY_IDS["logs"],
                "competency_id": COMPETENCY_IDS["observability"],
                "name": "Структурированные логи",
                "description": "Корреляция запросов и диагностические поля в логах.",
                "target_level": 2,
                "weight": 0.8,
            },
            {
                "id": SUB_COMPETENCY_IDS["metrics"],
                "competency_id": COMPETENCY_IDS["observability"],
                "name": "Метрики и алерты",
                "description": "SLI/SLO, метрики производительности и оповещения.",
                "target_level": 2,
                "weight": 0.8,
            },
            {
                "id": SUB_COMPETENCY_IDS["incident_response"],
                "competency_id": COMPETENCY_IDS["observability"],
                "name": "Работа с инцидентами",
                "description": "Диагностика, mitigation и postmortem.",
                "target_level": 2,
                "weight": 0.7,
            },
            {
                "id": SUB_COMPETENCY_IDS["cloud_basics"],
                "competency_id": COMPETENCY_IDS["cloud_networking"],
                "name": "Базовые облачные сервисы",
                "description": "Compute, storage и управление окружениями.",
                "target_level": 2,
                "weight": 0.7,
            },
            {
                "id": SUB_COMPETENCY_IDS["network_basics"],
                "competency_id": COMPETENCY_IDS["cloud_networking"],
                "name": "Сетевые основы",
                "description": "DNS, LB, TLS и сетевые политики доступа.",
                "target_level": 2,
                "weight": 0.7,
            },
            {
                "id": SUB_COMPETENCY_IDS["config_management"],
                "competency_id": COMPETENCY_IDS["cloud_networking"],
                "name": "Управление конфигурацией",
                "description": "Переменные окружения, параметры и секреты по средам.",
                "target_level": 2,
                "weight": 0.6,
            },
            {
                "id": SUB_COMPETENCY_IDS["unit_tests"],
                "competency_id": COMPETENCY_IDS["testing"],
                "name": "Unit-тесты",
                "description": "Изолированная проверка бизнес-логики и edge cases.",
                "target_level": 3,
                "weight": 1.0,
            },
            {
                "id": SUB_COMPETENCY_IDS["integration_tests"],
                "competency_id": COMPETENCY_IDS["testing"],
                "name": "Интеграционные тесты",
                "description": "Проверка взаимодействия модулей и persistence-слоя.",
                "target_level": 3,
                "weight": 1.0,
            },
            {
                "id": SUB_COMPETENCY_IDS["contract_tests"],
                "competency_id": COMPETENCY_IDS["testing"],
                "name": "Контрактные тесты API",
                "description": "Проверка совместимости и схемы HTTP-контрактов.",
                "target_level": 2,
                "weight": 0.8,
            },
            {
                "id": SUB_COMPETENCY_IDS["ddd_boundaries"],
                "competency_id": COMPETENCY_IDS["architecture"],
                "name": "Границы домена",
                "description": "Выделение bounded contexts и ответственность модулей.",
                "target_level": 2,
                "weight": 0.8,
            },
            {
                "id": SUB_COMPETENCY_IDS["clean_architecture"],
                "competency_id": COMPETENCY_IDS["architecture"],
                "name": "Clean Architecture",
                "description": "Слои, порты/адаптеры и зависимости через абстракции.",
                "target_level": 3,
                "weight": 0.9,
            },
            {
                "id": SUB_COMPETENCY_IDS["scalability"],
                "competency_id": COMPETENCY_IDS["architecture"],
                "name": "Масштабирование",
                "description": "Горизонтальное масштабирование и контроль состояния.",
                "target_level": 2,
                "weight": 0.8,
            },
            {
                "id": SUB_COMPETENCY_IDS["code_review"],
                "competency_id": COMPETENCY_IDS["team_process"],
                "name": "Code Review",
                "description": "Качество ревью, обратная связь и контроль рисков.",
                "target_level": 2,
                "weight": 0.7,
            },
            {
                "id": SUB_COMPETENCY_IDS["task_decomposition"],
                "competency_id": COMPETENCY_IDS["team_process"],
                "name": "Декомпозиция задач",
                "description": "Планирование, оценка и поставка инкрементов.",
                "target_level": 2,
                "weight": 0.7,
            },
            {
                "id": SUB_COMPETENCY_IDS["documentation"],
                "competency_id": COMPETENCY_IDS["team_process"],
                "name": "Техническая документация",
                "description": "Описание решений, runbooks и onboarding-документация.",
                "target_level": 1,
                "weight": 0.6,
            },
        ],
    )


def downgrade() -> None:
    op.execute(
        sa.delete(
            sa.table("sub_competencies", sa.column("id", sa.UUID(as_uuid=True)))
        ).where(
            sa.column("id", sa.UUID(as_uuid=True)).in_(
                tuple(SUB_COMPETENCY_IDS.values())
            )
        )
    )
    op.execute(
        sa.delete(
            sa.table("competencies", sa.column("id", sa.UUID(as_uuid=True)))
        ).where(
            sa.column("id", sa.UUID(as_uuid=True)).in_(tuple(COMPETENCY_IDS.values()))
        )
    )
    op.execute(
        sa.delete(sa.table("categories", sa.column("id", sa.UUID(as_uuid=True)))).where(
            sa.column("id", sa.UUID(as_uuid=True)).in_(tuple(CATEGORY_IDS.values()))
        )
    )
