from __future__ import annotations

from pathlib import Path

from domain.entities.job import Job
from domain.entities.value_objects import EngineType, JobStatus, LogLevel
from domain.usecases.run_asr import RunAsrPipeline
from tests.support.domain import (
    ControlledAsrService,
    LogRepositorySpy,
    StatusPublisherSpy,
    StubProfileProvider,
    TrackingJobRepository,
)


def make_job(job_id: str = "job-1") -> Job:
    return Job(
        id=job_id,
        source_path=Path("/tmp/audio.wav"),
        profile_id="juridico",
        engine=EngineType.OPENAI,
    )


def test_run_asr_pipeline_updates_status_and_language() -> None:
    job = make_job()
    repo = TrackingJobRepository(job)
    profile_provider = StubProfileProvider(translate=True)
    asr_service = ControlledAsrService()
    log_repo = LogRepositorySpy()

    status_publisher = StatusPublisherSpy()
    use_case = RunAsrPipeline(repo, profile_provider, asr_service, log_repo, status_publisher=status_publisher)
    result = use_case.execute(job.id)

    assert result.language == "en"
    assert repo.job.status == JobStatus.ASR_COMPLETED
    assert repo.job.language == "en"
    assert repo.job.duration_sec == 12.5
    assert profile_provider.calls == ["juridico"]
    assert asr_service.calls == ["translate"]
    assert ("asr_started", LogLevel.INFO) in log_repo.events
    assert ("asr_completed", LogLevel.INFO) in log_repo.events
    assert status_publisher.published.count(JobStatus.PROCESSING) == 1
    assert status_publisher.published[-1] == JobStatus.ASR_COMPLETED


def test_run_asr_pipeline_marks_failure_on_exception() -> None:
    job = make_job()
    repo = TrackingJobRepository(job)
    profile_provider = StubProfileProvider(translate=False)
    asr_service = ControlledAsrService(should_fail=True)
    log_repo = LogRepositorySpy()

    use_case = RunAsrPipeline(repo, profile_provider, asr_service, log_repo)
    try:
        use_case.execute(job.id)
    except RuntimeError:
        pass

    assert repo.job.status == JobStatus.FAILED
    assert repo.job.notes == "falha ASR"
    assert ("asr_failed", LogLevel.ERROR) in log_repo.events
