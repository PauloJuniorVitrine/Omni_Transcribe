from __future__ import annotations

import pytest

from domain.entities.job import Job
from domain.entities.transcription import PostEditResult, TranscriptionResult
from domain.entities.value_objects import EngineType, JobStatus
from domain.usecases.post_edit import PostEditTranscript
from tests.support.domain import LogRepositorySpy


class DummyJobRepository:
    def __init__(self, job: Job) -> None:
        self.job = job
        self.updates: list[JobStatus] = []

    def find_by_id(self, job_id: str) -> Job | None:
        return self.job if self.job.id == job_id else None

    def update(self, job: Job) -> Job:
        self.updates.append(job.status)
        self.job = job
        return job


class DummyProfileProvider:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def get(self, profile_id: str) -> dict[str, str]:
        self.calls.append(profile_id)
        return {"id": profile_id}


class DummyPostEditService:
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail

    def run(self, job: Job, profile, transcription: TranscriptionResult) -> PostEditResult:
        if self.should_fail:
            raise RuntimeError("falhou postedit")
        return PostEditResult(text=transcription.text.upper(), segments=[], language=transcription.language)


class DummyPublisher:
    def __init__(self) -> None:
        self.published: list[JobStatus] = []

    def publish(self, job: Job) -> None:
        self.published.append(job.status)


def _build_job(tmp_path, status=JobStatus.ASR_COMPLETED):
    return Job(
        id="job-post",
        source_path=tmp_path / "audio.wav",
        profile_id="geral",
        engine=EngineType.OPENAI,
        status=status,
    )


def test_post_edit_transcript_updates_status_and_logs(tmp_path):
    job = _build_job(tmp_path)
    repo = DummyJobRepository(job)
    profile_provider = DummyProfileProvider()
    service = DummyPostEditService()
    log_repo = LogRepositorySpy()
    publisher = DummyPublisher()
    use_case = PostEditTranscript(repo, profile_provider, service, log_repo, publisher)

    transcription = TranscriptionResult(text="ola", segments=[], language="pt")
    result = use_case.execute(job.id, transcription)

    assert result.text == "OLA"
    assert repo.updates[0] == JobStatus.POST_EDITING
    assert profile_provider.calls == ["geral"]
    assert publisher.published[0] == JobStatus.POST_EDITING
    assert any(event == "post_edit_completed" for event, _ in log_repo.events)


def test_post_edit_transcript_handles_failure(tmp_path):
    job = _build_job(tmp_path)
    repo = DummyJobRepository(job)
    profile_provider = DummyProfileProvider()
    service = DummyPostEditService(should_fail=True)
    log_repo = LogRepositorySpy()
    publisher = DummyPublisher()
    use_case = PostEditTranscript(repo, profile_provider, service, log_repo, publisher)

    transcription = TranscriptionResult(text="ola", segments=[], language="pt")
    with pytest.raises(RuntimeError):
        use_case.execute(job.id, transcription)

    assert repo.job.status == JobStatus.FAILED
    assert publisher.published[-1] == JobStatus.FAILED
    assert any(event == "post_edit_failed" for event, _ in log_repo.events)
