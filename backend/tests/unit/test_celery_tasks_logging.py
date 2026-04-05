from __future__ import annotations

import pytest

from competency_system.application.ports.llm_jobs import LLMJobType
from competency_system.infrastructure.llm.celery_tasks import (
    dispatch_llm_job_task,
)
from competency_system.infrastructure.llm.errors import LLMAdapterError
from competency_system.infrastructure.settings import Settings

pytestmark = pytest.mark.unit


class _DummyTask:
    def __init__(self, *, retries: int = 0) -> None:
        self.request = type(
            "Request",
            (),
            {"id": "job-123", "retries": retries},
        )()
        self.retry_calls: list[dict[str, object]] = []

    def retry(self, **kwargs):  # type: ignore[no-untyped-def]
        self.retry_calls.append(kwargs)
        raise RuntimeError("retry_invoked")


def _settings() -> Settings:
    return Settings(
        celery_retry_attempts=3,
        celery_retry_backoff_seconds=2,
        celery_retry_backoff_max_seconds=30,
        celery_queue_name="llm_jobs",
    )


async def _run_ok(*args, **kwargs) -> None:  # type: ignore[no-untyped-def]
    return None


async def _run_transient_error(*args, **kwargs) -> None:  # type: ignore[no-untyped-def]
    raise LLMAdapterError("temporary llm error")


def test_dispatch_llm_job_task_logs_success(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    task = _DummyTask(retries=0)
    monkeypatch.setattr(
        "competency_system.infrastructure.llm.celery_tasks.get_settings",
        _settings,
    )
    monkeypatch.setattr(
        "competency_system.infrastructure.llm.celery_tasks._run_dispatch",
        _run_ok,
    )

    dispatch_llm_job_task.run.__func__(
        task,
        job_type=str(LLMJobType.TASK_MAPPING),
        payload={"task_id": "t1"},
    )

    output = capsys.readouterr().out
    assert "llm_job_started" in output
    assert "llm_job_finished" in output


def test_dispatch_llm_job_task_logs_retry_summary_for_transient_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    task = _DummyTask(retries=0)
    monkeypatch.setattr(
        "competency_system.infrastructure.llm.celery_tasks.get_settings",
        _settings,
    )
    monkeypatch.setattr(
        "competency_system.infrastructure.llm.celery_tasks._run_dispatch",
        _run_transient_error,
    )

    with pytest.raises(RuntimeError, match="retry_invoked"):
        dispatch_llm_job_task.run.__func__(
            task,
            job_type=str(LLMJobType.TASK_MAPPING),
            payload={"task_id": "t1"},
        )

    output = capsys.readouterr().out
    assert "llm_job_retry_scheduled" in output
    assert len(task.retry_calls) == 1


def test_dispatch_llm_job_task_logs_full_failure_on_final_attempt(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    task = _DummyTask(retries=2)
    monkeypatch.setattr(
        "competency_system.infrastructure.llm.celery_tasks.get_settings",
        _settings,
    )
    monkeypatch.setattr(
        "competency_system.infrastructure.llm.celery_tasks._run_dispatch",
        _run_transient_error,
    )

    with pytest.raises(LLMAdapterError):
        dispatch_llm_job_task.run.__func__(
            task,
            job_type=str(LLMJobType.TASK_MAPPING),
            payload={"task_id": "t1", "raw_text": "full data"},
        )

    output = capsys.readouterr().out
    assert "llm_job_failed" in output
