from __future__ import annotations

from competency_system.application.dtos.task import TaskSyncPeriodDTO


class TaskSyncPayloadDTO(TaskSyncPeriodDTO):
    prompt_version: str | None = None
