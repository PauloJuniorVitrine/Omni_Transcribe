from __future__ import annotations

from typing import List, Optional, Protocol

from ..entities.artifact import Artifact
from ..entities.transcription import PostEditResult, TranscriptionResult
from ..ports.repositories import LogRepository
from ..entities.log_entry import LogEntry
from ..entities.value_objects import LogLevel
from .generate_artifacts import GenerateArtifacts
from .post_edit import PostEditTranscript
from .retry_or_reject import RetryDecision, RetryOrRejectJob
from .run_asr import RunAsrPipeline


class AccuracyGuard(Protocol):
    def evaluate(
        self, job_id: str, transcription: TranscriptionResult, post_edit: PostEditResult
    ) -> None:
        ...


class ProcessJobPipeline:
    """High-level orchestration from ASR through artifact generation."""

    def __init__(
        self,
        asr_use_case: RunAsrPipeline,
        post_edit_use_case: PostEditTranscript,
        artifact_use_case: GenerateArtifacts,
        log_repository: LogRepository,
        retry_handler: Optional[RetryOrRejectJob] = None,
        accuracy_guard: Optional[AccuracyGuard] = None,
        allow_retry: bool = False,
    ) -> None:
        self.asr_use_case = asr_use_case
        self.post_edit_use_case = post_edit_use_case
        self.artifact_use_case = artifact_use_case
        self.log_repository = log_repository
        self.retry_handler = retry_handler
        self.accuracy_guard = accuracy_guard
        self.allow_retry = allow_retry

    def execute(self, job_id: str) -> List[Artifact]:
        transcription: Optional[TranscriptionResult] = None
        post_edit: Optional[PostEditResult] = None
        current_stage = "asr"
        try:
            transcription = self.asr_use_case.execute(job_id)
            current_stage = "post_edit"
            post_edit = self.post_edit_use_case.execute(job_id, transcription)
            if self.accuracy_guard:
                self.accuracy_guard.evaluate(job_id, transcription, post_edit)
            current_stage = "artifacts"
            artifacts = self.artifact_use_case.execute(job_id, post_edit)
            return artifacts
        except Exception as exc:
            self.log_repository.append(
                LogEntry(
                    job_id=job_id,
                    event="pipeline_failed",
                    level=LogLevel.ERROR,
                    message=str(exc),
                )
            )
            if self.retry_handler:
                payload = {"stage": current_stage, "exception": exc.__class__.__name__}
                self.retry_handler.execute(
                    RetryDecision(
                        job_id=job_id,
                        error_message=str(exc),
                        retryable=self._should_retry(exc, current_stage),
                        stage=current_stage,
                        payload=payload,
                    )
                )
            raise

    def _should_retry(self, exc: Exception, stage: str) -> bool:
        return bool(self.allow_retry)
