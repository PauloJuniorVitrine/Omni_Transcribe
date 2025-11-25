from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional, Protocol, TypeVar

from ..entities.artifact import Artifact
from ..entities.transcription import PostEditResult, TranscriptionResult
from ..ports.repositories import LogRepository
from ..entities.log_entry import LogEntry
from ..entities.value_objects import LogLevel
from .generate_artifacts import GenerateArtifacts
from .post_edit import PostEditTranscript
from .retry_or_reject import RetryDecision, RetryOrRejectJob
from .run_asr import RunAsrPipeline
from infrastructure.telemetry.metrics_logger import (
    notify_alert,
    record_metric,
    record_histogram,
)


T = TypeVar("T")


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
            transcription = self._run_stage("asr", lambda: self.asr_use_case.execute(job_id), job_id)
            self._record_asr_metrics(job_id, transcription)
            current_stage = "post_edit"
            post_edit = self._run_stage(
                "post_edit", lambda: self.post_edit_use_case.execute(job_id, transcription), job_id
            )
            if self.accuracy_guard:
                self.accuracy_guard.evaluate(job_id, transcription, post_edit)
            current_stage = "artifacts"
            artifact_result = self._run_stage(
                "artifacts", lambda: self.artifact_use_case.execute(job_id, post_edit), job_id
            )
            artifacts = list(artifact_result)
            self._record_artifact_metrics(job_id, artifacts)
            record_metric("pipeline.completed", {"job_id": job_id, "artifact_count": len(artifacts)})
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
            notify_alert(
                "pipeline.failed",
                {
                    "job_id": job_id,
                    "stage": current_stage,
                    "error": exc.__class__.__name__,
                    "message": str(exc),
                },
            )
            if self.retry_handler:
                retryable = self._should_retry(exc, current_stage)
                payload = {
                    "stage": current_stage,
                    "exception": exc.__class__.__name__,
                    "message": str(exc),
                    "retryable": retryable,
                }
                self.retry_handler.execute(
                    RetryDecision(
                        job_id=job_id,
                        error_message=str(exc),
                        retryable=retryable,
                        stage=current_stage,
                        payload=payload,
                    )
                )
                record_metric(
                    "pipeline.retry.triggered",
                    {
                        "job_id": job_id,
                        "stage": current_stage,
                        "retryable": retryable,
                        "exception": exc.__class__.__name__,
                    },
                )
            raise

    def _run_stage(self, stage_name: str, fn: Callable[[], T], job_id: str) -> T:
        start = time.perf_counter()
        success = False
        try:
            result = fn()
            success = True
            return result
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            payload: Dict[str, Any] = {
                "job_id": job_id,
                "stage": stage_name,
                "duration_ms": round(duration_ms, 2),
                "success": success,
            }
            record_metric("pipeline.stage.duration", payload)
            record_histogram(
                "pipeline.stage.latency",
                duration_ms,
                bucket_size=50,
                tags={"stage": stage_name, "success": success},
            )

    def _record_asr_metrics(self, job_id: str, transcription: TranscriptionResult) -> None:
        metadata_chunk_count = transcription.metadata.get("chunk_count")
        record_metric(
            "pipeline.asr.completed",
            {
                "job_id": job_id,
                "engine": transcription.engine,
                "language": transcription.language,
                "chunked": transcription.metadata.get("chunked", False),
                "chunk_count": metadata_chunk_count,
                "duration_sec": transcription.duration_sec,
            },
        )
        if metadata_chunk_count is not None:
            try:
                chunk_value = float(metadata_chunk_count)
            except (TypeError, ValueError):
                chunk_value = 0.0
            record_histogram(
                "pipeline.asr.chunk_count",
                chunk_value,
                bucket_size=1,
                tags={"chunked": transcription.metadata.get("chunked", False)},
            )

    def _record_artifact_metrics(self, job_id: str, artifacts: List[Artifact]) -> None:
        record_metric(
            "pipeline.artifacts.generated",
            {
                "job_id": job_id,
                "artifact_count": len(artifacts),
                "artifact_types": [artifact.artifact_type.value for artifact in artifacts],
            },
        )

    def _should_retry(self, exc: Exception, stage: str) -> bool:
        return bool(self.allow_retry)
