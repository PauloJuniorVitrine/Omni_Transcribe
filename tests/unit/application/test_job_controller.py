from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from application.controllers.job_controller import JobController
from domain.entities.job import Job
from domain.entities.value_objects import EngineType, JobStatus
from domain.usecases.retry_or_reject import RetryDecision


class DummyJobRepo:
    def __init__(self):
        self.jobs = [
            Job(
                id="job-1",
                source_path=Path("inbox/audio.wav"),
                profile_id="geral",
                engine=EngineType.OPENAI,
                status=JobStatus.PENDING,
            )
        ]

    def list_recent(self, limit: int = 20):
        return self.jobs[:limit]


class DummyCreateJobUseCase:
    def __init__(self):
        self.executed = False

    def execute(self, input_data):
        self.executed = True
        return Job(
            id="job-new",
            source_path=input_data.source_path,
            profile_id=input_data.profile_id or "geral",
            engine=input_data.engine,
        )


class DummyPipeline:
    def __init__(self):
        self.records = []

    def execute(self, job_id: str):
        self.records.append(job_id)


class DummyRetry:
    def __init__(self):
        self.decisions = []

    def execute(self, decision: RetryDecision):
        self.decisions.append(decision)
        return Job(
            id=decision.job_id,
            source_path=Path("inbox/file.wav"),
            profile_id="geral",
            engine=EngineType.OPENAI,
            status=JobStatus.PENDING,
        )


def test_list_jobs_returns_from_repo():
    repo = DummyJobRepo()
    controller = JobController(repo, DummyCreateJobUseCase(), None, DummyRetry())
    jobs, has_more = controller.list_jobs()
    assert len(jobs) == 1 and jobs[0].id == "job-1"
    assert has_more is False


def test_ingest_file_calls_use_case():
    repo = DummyJobRepo()
    create_use_case = DummyCreateJobUseCase()
    controller = JobController(repo, create_use_case, None, DummyRetry())
    job = controller.ingest_file(Path("inbox/sample.wav"), "profile-x", EngineType.OPENAI)
    assert create_use_case.executed is True
    assert job.id == "job-new"


def test_process_job_requires_pipeline():
    repo = DummyJobRepo()
    controller = JobController(repo, DummyCreateJobUseCase(), None, DummyRetry())
    with pytest.raises(RuntimeError):
        controller.process_job("job-1")

    pipeline = DummyPipeline()
    controller = JobController(repo, DummyCreateJobUseCase(), pipeline, DummyRetry())
    controller.process_job("job-1")
    assert pipeline.records == ["job-1"]


def test_requeue_job_uses_retry():
    repo = DummyJobRepo()
    retry_use_case = DummyRetry()
    controller = JobController(repo, DummyCreateJobUseCase(), None, retry_use_case)
    job = controller.requeue_job("job-xyz", "error", retryable=False)
    assert job.id == "job-xyz"
    assert retry_use_case.decisions[-1].retryable is False
