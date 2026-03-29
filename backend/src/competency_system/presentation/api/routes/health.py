from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from competency_system.application.use_cases.health import HealthCheckUseCase
from competency_system.presentation.api.dependencies import get_health_check_use_case

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str = "ok"
    database: str = "ok"


@router.get("/health", response_model=HealthResponse)
async def health_check(
    use_case: Annotated[HealthCheckUseCase, Depends(get_health_check_use_case)],
) -> HealthResponse:
    result = await use_case.execute()
    return HealthResponse(status=result.status, database=result.database)
