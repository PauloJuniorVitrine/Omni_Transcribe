from __future__ import annotations

import pytest
from pathlib import Path

from domain.entities.artifact import Artifact
from domain.entities.transcription import PostEditResult, TranscriptionResult, Segment
from domain.entities.value_objects import ArtifactType, LogLevel
from domain.entities.log_entry import LogEntry
from domain.usecases.pipeline import ProcessJobPipeline
from domain.usecases.retry_or_reject import RetryDecision


class _StubLogRepo:
    def __init__(self) -> None:
        self.entries: list[LogEntry] = []

    def append(self, entry: LogEntry) -> None:
        self.entries.append(entry)


class _StubRetryHandler:
    def __init__(self) -> None:
        self.called_with: RetryDecision | None = None

    def execute(self, decision: RetryDecision) -> None:
        self.called_with = decision


class _StubAccuracyGuard:
    def __init__(self) -> None:
        self.called_with: tuple[str, TranscriptionResult, PostEditResult] | None = None

    def evaluate(self, job_id: str, transcription: TranscriptionResult, post_edit: PostEditResult) -> None:
        self.called_with = (job_id, transcription, post_edit)


def _successful_asr(result_language: str = "pt") -> TranscriptionResult:
    return TranscriptionResult(
        text="ok",
        segments=[Segment(id=0, start=0.0, end=1.0, text="ok")],
        language=result_language,
        duration_sec=1.0,
        engine="openai",
    )


def test_pipeline_success_invokes_guard_and_returns_artifacts(tmp_path):
    log_repo = _StubLogRepo()
    guard = _StubAccuracyGuard()

    class AsrUseCase:
        def execute(self, job_id: str) -> TranscriptionResult:
            return _successful_asr()

    class PostEditUseCase:
        def execute(self, job_id: str, transcription: TranscriptionResult) -> PostEditResult:
            assert transcription.text == "ok"
            return PostEditResult(text="ok-post", segments=transcription.segments, flags=[], language="pt")

    class ArtifactUseCase:
        def execute(self, job_id: str, post_edit: PostEditResult):
            path = tmp_path / f"{job_id}.txt"
            path.write_text("content", encoding="utf-8")
            yield Artifact(id="a1", job_id=job_id, artifact_type=ArtifactType.TRANSCRIPT_TXT, path=path)

    pipeline = ProcessJobPipeline(
        asr_use_case=AsrUseCase(),
        post_edit_use_case=PostEditUseCase(),
        artifact_use_case=ArtifactUseCase(),
        log_repository=log_repo,
        retry_handler=None,
        accuracy_guard=guard,
    )

    artifacts = list(pipeline.execute("job-1"))

    assert len(artifacts) == 1
    assert artifacts[0].artifact_type == ArtifactType.TRANSCRIPT_TXT
    assert guard.called_with is not None
    assert guard.called_with[0] == "job-1"
    assert not log_repo.entries


def test_pipeline_error_triggers_retry_with_stage():
    log_repo = _StubLogRepo()
    retry_handler = _StubRetryHandler()

    class AsrUseCase:
        def execute(self, job_id: str) -> TranscriptionResult:
            return _successful_asr()

    class PostEditUseCase:
        def execute(self, job_id: str, transcription: TranscriptionResult) -> PostEditResult:
            raise RuntimeError("boom")

    class ArtifactUseCase:
        def execute(self, job_id: str, post_edit: PostEditResult):
            return []

    pipeline = ProcessJobPipeline(
        asr_use_case=AsrUseCase(),
        post_edit_use_case=PostEditUseCase(),
        artifact_use_case=ArtifactUseCase(),
        log_repository=log_repo,
        retry_handler=retry_handler,
        allow_retry=True,
    )

    with pytest.raises(RuntimeError):
        pipeline.execute("job-err")

    # retry handler invoked with post_edit stage payload
    assert retry_handler.called_with is not None
    assert retry_handler.called_with.job_id == "job-err"
    assert retry_handler.called_with.stage == "post_edit"
    assert retry_handler.called_with.retryable is True
    # error logged
    assert any(entry.event == "pipeline_failed" and entry.level == LogLevel.ERROR for entry in log_repo.entries)


def test_pipeline_error_marks_non_retryable_when_disabled():
    log_repo = _StubLogRepo()
    retry_handler = _StubRetryHandler()

    class AsrUseCase:
        def execute(self, job_id: str) -> TranscriptionResult:
            raise RuntimeError("asr-fail")

    pipeline = ProcessJobPipeline(
        asr_use_case=AsrUseCase(),
        post_edit_use_case=None,  # type: ignore[arg-type]
        artifact_use_case=None,  # type: ignore[arg-type]
        log_repository=log_repo,
        retry_handler=retry_handler,
        allow_retry=False,
    )

    with pytest.raises(RuntimeError):
        pipeline.execute("job-no-retry")

    assert retry_handler.called_with is not None
    assert retry_handler.called_with.retryable is False
    assert retry_handler.called_with.stage == "asr"


def test_pipeline_accuracy_guard_failure_logs_and_retries(tmp_path):
    log_repo = _StubLogRepo()
    retry_handler = _StubRetryHandler()

    class AsrUseCase:
        def execute(self, job_id: str) -> TranscriptionResult:
            return _successful_asr()

    class PostEditUseCase:
        def execute(self, job_id: str, transcription: TranscriptionResult) -> PostEditResult:
            return PostEditResult(text="ok-post", segments=transcription.segments, flags=[], language="pt")

    class ArtifactUseCase:
        def execute(self, job_id: str, post_edit: PostEditResult):
            path = tmp_path / f"{job_id}.txt"
            path.write_text("content", encoding="utf-8")
            yield Artifact(id="a1", job_id=job_id, artifact_type=ArtifactType.TRANSCRIPT_TXT, path=path)

    class FailingGuard:
        def evaluate(self, job_id: str, transcription: TranscriptionResult, post_edit: PostEditResult) -> None:
            raise RuntimeError("accuracy-too-low")

    pipeline = ProcessJobPipeline(
        asr_use_case=AsrUseCase(),
        post_edit_use_case=PostEditUseCase(),
        artifact_use_case=ArtifactUseCase(),
        log_repository=log_repo,
        retry_handler=retry_handler,
        accuracy_guard=FailingGuard(),
        allow_retry=True,
    )

    with pytest.raises(RuntimeError):
        list(pipeline.execute("job-accuracy"))

    assert any(entry.event == "pipeline_failed" and "accuracy" in entry.message for entry in log_repo.entries)
    assert retry_handler.called_with is not None
    assert retry_handler.called_with.job_id == "job-accuracy"
    assert retry_handler.called_with.stage == "post_edit"
    assert retry_handler.called_with.retryable is True
