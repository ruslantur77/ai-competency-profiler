# Competency System - Backend

AI-powered competency assessment system for evaluating candidates based on test results and code analysis.

## Architecture

Clean Architecture with the following layers:

```
src/competency_system/
├── domain/                 # Business entities and rules (no dependencies)
│   ├── entities/
│   ├── value_objects/
│   └── services/
├── application/            # Use cases and application logic
│   ├── ports/             # Interfaces for infrastructure
│   ├── dtos/              # Data transfer objects
│   └── use_cases/         # Business operations
├── infrastructure/         # External implementations
│   ├── persistence/       # Database repositories
│   ├── llm/               # LLM integrations
│   └── external/          # External API clients
└── presentation/          # Entry points
    ├── api/               # FastAPI endpoints
    └── airflow/           # Airflow DAGs
```

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.12+ (for local development)

### 1. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys
# Add TESTING_SYSTEM_WEBHOOK_SECRET if webhook verification is enabled
```

### 2. Start Services

```bash
# Build and start all services
docker-compose up -d --build

# Or step by step:
docker-compose up -d postgres
docker-compose up -d api
docker-compose up -d airflow-init airflow-webserver airflow-scheduler airflow-triggerer
```

### 3. Run Migrations

```bash
# Apply database migrations
docker-compose exec api alembic upgrade head

# Or locally with uv:
uv run alembic upgrade head
```

### 4. Access Services

| Service | URL | Credentials |
|---------|-----|-------------|
| API Docs | http://localhost:8000/docs | - |
| Health Check | http://localhost:8000/health | - |
| Airflow UI | http://localhost:8080 | admin / admin |
| PostgreSQL | localhost:5432 | app/app |

## Development

### Local Setup (without Docker)

```bash
# Install dependencies with uv
uv sync --all-extras

# Or with pip
pip install -e ".[dev]"

# Run migrations
alembic upgrade head

# Start API
uvicorn competency_system.presentation.api.main:app --reload
```

### Code Quality

```bash
# Format code
ruff format .
ruff check . --fix

# Type checking
mypy src/

# Run tests
pytest

# Run tests with coverage
pytest --cov=src --cov-report=html

# Run repository/UoW integration tests against PostgreSQL
TEST_DB_URL=postgresql://user:pass@127.0.0.1:5432/app pytest -m integration_repo
# or
TEST_DB_HOST=127.0.0.1 TEST_DB_PORT=5432 TEST_DB_NAME=app TEST_DB_USER=user TEST_DB_PASS=pass pytest -m integration_repo
# or
pytest -m integration_repo --test-db-url postgresql://user:pass@127.0.0.1:5432/app
```

CI mirrors the same quality gates with GitHub Actions:
- `ruff check src tests`
- `mypy src`
- `pytest`

API and background jobs emit structured JSON logs.

### Project Structure Details

#### Domain Layer (`domain/`)
Pure business logic without external dependencies:
- **Entities**: Business objects with identity (Vacancy, Candidate, etc.)
- **Value Objects**: Immutable data (CompetencyLevel, VacancyStatus)
- **Domain Services**: Complex business operations

#### Application Layer (`application/`)
Orchestration of domain objects:
- **Ports**: Abstract interfaces for repositories and gateways
- **DTOs**: Data structures for use case input/output
- **Use Cases**: Business operations (ExtractVacancyGraph, AssessCandidate, etc.)

#### Infrastructure Layer (`infrastructure/`)
External implementations:
- **Persistence**: SQLAlchemy repositories
- **LLM**: OpenRouter/OpenAI integration
- **External**: Test system API clients

#### Presentation Layer (`presentation/`)
Entry points:
- **API**: FastAPI routes and middleware
- **Airflow**: DAG definitions for batch processing

## API Endpoints

### Auth
- `POST /api/v1/auth/login` - Login via form-data (`username`, `password`), returns access token and sets refresh cookie
- `POST /api/v1/auth/refresh` - Rotate token pair using refresh cookie
- `POST /api/v1/auth/logout` - Revoke refresh token and clear cookie

### Vacancies
- `GET /api/v1/vacancies` - List vacancies, supports `status_filter=draft,ready,...`
- `GET /api/v1/vacancies/review-queue` - Expert queue (draft/extracting/failed)
- `POST /api/v1/vacancies` - Create vacancy and start extraction
- `GET /api/v1/vacancies/{id}` - Get vacancy details
- `GET /api/v1/vacancies/{id}/graph` - Get competency graph
- `PATCH /api/v1/vacancies/{id}/graph` - Update graph (expert validation)
- `PATCH /api/v1/vacancies/{id}/status` - Update vacancy status (`draft/extracting/ready/failed`)

### Candidates
- `GET /api/v1/vacancies/{id}/rankings` - Get cached vacancy rankings
- `GET /api/v1/vacancies/{id}/ranking` - Force ranking recalculation (legacy path)
- `GET /api/v1/vacancies/{id}/candidates` - Legacy alias for recalculation path
- `GET /api/v1/candidates/{id}/profile` - Get detailed competency profile

Ranking model (MVP): vector similarity (cosine-based) with required/desired budgets and explainable per-competency breakdown.

### Admin Users
- `GET /api/v1/admin/users` - List users
- `POST /api/v1/admin/users` - Create user with role
- `PATCH /api/v1/admin/users/{id}/role` - Change user role
- `PATCH /api/v1/admin/users/{id}/status` - Enable/disable user

### Tasks
- `POST /api/v1/webhook/task-completed` - Webhook from testing system, protected by `X-Webhook-Secret`
- `GET /api/v1/tasks/{id}/mapping` - Get task-to-competencies mapping

## Testing System Integration

### Incoming Webhook (Testing System → Our System)

```http
POST /api/v1/webhook/task-completed
Content-Type: application/json
X-Webhook-Secret: {shared-secret}

{
  "event_id": "string (idempotency key)",
  "vacancy_id": "uuid",
  "candidate_external_id": "string",
  "task_external_id": "string",
  "type": "CODE|TEST",
  "code": "string (optional, for CODE type)",
  "question_answers": [{"question": "string", "answer": "string"}],
  "passed": 5,
  "total": 10,
  "attempts": 3,
  "duration_seconds": 600
}
```

The shared secret is configured via `TESTING_SYSTEM_WEBHOOK_SECRET`. If the secret is empty, local development remains permissive.

### Outgoing API (Our System → Testing System)

```http
GET /external/tasks
Authorization: Bearer {token}

Response: [
  {
    "external_id": "string",
    "title": "string",
    "description": "string",
    "type": "CODE|TEST",
    "tags": ["string"]
  }
]
```

## Airflow DAGs

| DAG | Schedule | Description |
|-----|----------|-------------|
| `vacancy_extraction` | Triggered | Extract competencies from vacancy (3-step LLM pipeline) |
| `task_sync` | Daily | Sync tasks from testing system |
| `candidate_assessment` | Triggered | Assess candidate and update profile, then recalculate ranking |
| `ranking_recalculation` | Triggered | Recalculate rankings for a vacancy |

## Troubleshooting

### Reset Database

```bash
docker-compose down -v
docker-compose up -d postgres
docker-compose exec api alembic upgrade head
```

### View Logs

```bash
# API logs
docker-compose logs -f api

# PostgreSQL logs
docker-compose logs -f postgres
```

## License

Private - All rights reserved.

## API Base Path
All HTTP endpoints are served under `/api/v1`.

## Sandbox Test Policy
Tests can be authored and updated in this repository, but they must not be executed in sandbox environments.
