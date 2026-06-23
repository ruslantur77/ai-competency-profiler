<div align="center">
  <picture>
      <img  src="https://github.com/user-attachments/assets/e8d9640b-4ffc-4dfe-9a46-dda06184dc53" width="25%"/>
  </picture>
</div>


# AI Competency Profiler

AI Competency Profiler помогает строить компетентностный профиль специалиста по тексту вакансии. Система извлекает требования, группирует их в структуру компетенций и дает интерфейс для экспертной проверки и ручной корректировки результата.

## Основные возможности

- извлечение требований и навыков из вакансии;
- формирование структуры компетенций и подкомпетенций;
- визуальная работа с результатом в веб-интерфейсе;
- ручная корректировка и валидация экспертами;
- серверный пайплайн с LLM-обработкой и хранением данных.

## Структура проекта

- `frontend/` — клиентская часть на React + Vite;
- `backend/` — API, бизнес-логика, фоновые задачи и инфраструктурные интеграции.
- `mock_testing_system/` — отдельный легкий mock внешней тестовой системы для генерации задач по периоду.

## Требования

- Node.js 18+ для frontend-разработки;
- Docker и Docker Compose для полного запуска backend-части (подробно в backend README).

## Быстрый старт (frontend)

```bash
cd frontend
npm install
npm run dev
```

После запуска интерфейс доступен на `http://localhost:5173`.

## Backend

Backend реализован на FastAPI и покрывает основной серверный контур: обработку вакансий, LLM-этапы, хранение данных и фоновые задачи (PostgreSQL, Redis, Celery, Airflow).

Полные инструкции по запуску, переменным окружения, сервисам и портам смотрите в [backend/README.md](backend/README.md).

## Unified Docker Compose (root)

Для запуска полного стека `frontend + backend + nginx` без blue/green:

```bash
cp backend/.env.example backend/.env
export DOCKER_GID=$(stat -c '%g' /var/run/docker.sock)
docker compose --env-file backend/.env up -d --build
```

Точки входа:
- App (через nginx): `http://localhost/`
- API (через nginx): `http://localhost/api/v1`
- Swagger (через nginx): `http://localhost/api/docs`

## Документация

- Backend: [backend/README.md](backend/README.md)
- Frontend (шаблонный файл): `frontend/README.md`
- Mock внешней системы: [mock_testing_system/README.md](mock_testing_system/README.md)
