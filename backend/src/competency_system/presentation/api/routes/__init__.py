from competency_system.presentation.api.routes.admin_tasks import (
    router as admin_tasks_router,
)
from competency_system.presentation.api.routes.admin_users import (
    router as admin_users_router,
)
from competency_system.presentation.api.routes.auth import router as auth_router
from competency_system.presentation.api.routes.candidates import (
    router as candidates_router,
)
from competency_system.presentation.api.routes.health import router as health_router
from competency_system.presentation.api.routes.ontology import (
    router as ontology_router,
)
from competency_system.presentation.api.routes.ranking import router as ranking_router
from competency_system.presentation.api.routes.tasks import router as tasks_router
from competency_system.presentation.api.routes.tasks import webhook_router
from competency_system.presentation.api.routes.vacancies import (
    router as vacancies_router,
)

__all__ = [
    "health_router",
    "auth_router",
    "vacancies_router",
    "ontology_router",
    "tasks_router",
    "admin_tasks_router",
    "admin_users_router",
    "webhook_router",
    "candidates_router",
    "ranking_router",
]
