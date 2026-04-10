from __future__ import annotations

from competency_system.application.dtos.task import TaskSyncRequestDTO


class TaskSyncPayloadDTO(TaskSyncRequestDTO):
    prompt_version: str | None = None
