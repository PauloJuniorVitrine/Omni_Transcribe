from __future__ import annotations

from pathlib import Path

from application.services.rejected_logger import FilesystemRejectedLogger
from domain.entities.job import Job
from domain.entities.value_objects import EngineType, JobStatus
from domain.usecases.retry_or_reject import RetryDecision, RetryOrRejectJob
from tests.support.domain import LogRepositorySpy, TrackingJobRepository, StatusPublisherSpy


def test_retry_or_reject_writes_failure_file(tmp_path: Path) -> None:
    job = Job(
        id="job-err",
        source_path=tmp_path / "audio.wav",
        profile_id="geral",
        engine=EngineType.OPENAI,
    )
    repo = TrackingJobRepository(job)
    log_repo = LogRepositorySpy()
    rejected_logger = FilesystemRejectedLogger(tmp_path / "rejected")
    use_case = RetryOrRejectJob(repo, log_repo, rejected_logger)

    decision = RetryDecision(
        job_id=job.id,
        error_message="falha grave",
        retryable=False,
        stage="asr",
        payload={"info": "detalhe"},
    )
    use_case.execute(decision)

    assert repo.job.status == JobStatus.REJECTED
    files = list((tmp_path / "rejected" / job.id).glob("failure_*.json"))
    assert files, "Esperava arquivo em rejected/"
    data = files[0].read_text(encoding="utf-8")
    assert "falha grave" in data
    assert '"stage": "asr"' in data


def test_retry_or_reject_requeues_and_notifies(tmp_path: Path) -> None:
    job = Job(
        id="job-retry",
        source_path=tmp_path / "audio.wav",
        profile_id="geral",
        engine=EngineType.OPENAI,
        status=JobStatus.FAILED,
    )
    repo = TrackingJobRepository(job)
    log_repo = LogRepositorySpy()
    publisher = StatusPublisherSpy()
    use_case = RetryOrRejectJob(repo, log_repo, rejected_logger=None, status_publisher=publisher)

    decision = RetryDecision(job_id=job.id, error_message="erro temporario", retryable=True)
    updated = use_case.execute(decision)

    assert updated.status == JobStatus.PENDING
    assert repo.updates[-1] == JobStatus.PENDING
    assert publisher.published[-1] == JobStatus.PENDING
    assert any(event == "job_requeued" for event, _ in log_repo.events)
