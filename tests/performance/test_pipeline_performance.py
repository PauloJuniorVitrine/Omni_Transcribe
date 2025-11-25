from __future__ import annotations

import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from domain.entities.value_objects import EngineType
from domain.usecases.create_job import CreateJobFromInbox, CreateJobInput
from domain.usecases.generate_artifacts import GenerateArtifacts
from domain.usecases.pipeline import ProcessJobPipeline
from domain.usecases.post_edit import PostEditTranscript
from domain.usecases.retry_or_reject import RetryOrRejectJob
from domain.usecases.run_asr import RunAsrPipeline
from infrastructure.database.profile_provider import FilesystemProfileProvider
from application.services.artifact_builder import FilesystemArtifactBuilder
from application.services.subtitle_formatter import SubtitleFormatter
from application.services.validator_service import TranscriptValidator
from application.services.rejected_logger import FilesystemRejectedLogger
from application.services.sheet_service import CsvSheetService
from application.services.status_publisher import SheetStatusPublisher
from tests.support import stubs


def build_pipeline(tmp_path: Path):
    job_repo = stubs.MemoryJobRepository()
    artifact_repo = stubs.MemoryArtifactRepository()
    log_repo = stubs.MemoryLogRepository()
    profile_provider = FilesystemProfileProvider(Path("profiles"))
    sheet_service = CsvSheetService(tmp_path / "perf_log.csv")
    status_publisher = SheetStatusPublisher(sheet_service)
    rejected_logger = FilesystemRejectedLogger(tmp_path / "rejected")

    create_job = CreateJobFromInbox(
        job_repository=job_repo,
        profile_provider=profile_provider,
        log_repository=log_repo,
        status_publisher=status_publisher,
    )
    asr = RunAsrPipeline(
        job_repository=job_repo,
        profile_provider=profile_provider,
        asr_service=stubs.StubAsrService("pipeline perf"),
        log_repository=log_repo,
        status_publisher=status_publisher,
    )
    post = PostEditTranscript(
        job_repository=job_repo,
        profile_provider=profile_provider,
        post_edit_service=stubs.StubPostEditService(),
        log_repository=log_repo,
        status_publisher=status_publisher,
    )
    builder = FilesystemArtifactBuilder(tmp_path / "output", SubtitleFormatter(), TranscriptValidator())
    artifacts = GenerateArtifacts(
        job_repository=job_repo,
        artifact_repository=artifact_repo,
        artifact_builder=builder,
        log_repository=log_repo,
        profile_provider=profile_provider,
        status_publisher=status_publisher,
    )
    retry = RetryOrRejectJob(job_repo, log_repo, rejected_logger=rejected_logger, status_publisher=status_publisher)
    pipeline = ProcessJobPipeline(asr, post, artifacts, log_repo, retry_handler=retry)
    return create_job, pipeline, job_repo


def _run_single_job(create_job, pipeline, tmp_path, index: int) -> tuple[object, float]:
    audio_file = tmp_path / f"audio-{index}.wav"
    audio_file.write_bytes(b"fake audio")
    job = create_job.execute(CreateJobInput(source_path=audio_file, engine=EngineType.OPENAI))
    start = time.perf_counter()
    pipeline.execute(job.id)
    return job, time.perf_counter() - start


@pytest.mark.performance
def test_pipeline_average_execution_time(tmp_path):
    create_job, pipeline, job_repo = build_pipeline(tmp_path)
    results = [_run_single_job(create_job, pipeline, tmp_path, idx) for idx in range(5)]
    durations = [duration for _, duration in results]
    avg = sum(durations) / len(durations)
    max_allowed = 0.6
    assert avg < max_allowed, f"Pipeline médio {avg:.4f}s acima do limite {max_allowed}s"
    stored_job = job_repo.find_by_id(results[-1][0].id)
    assert stored_job and stored_job.status.value == "awaiting_review"


@pytest.mark.performance
@pytest.mark.parametrize("num_jobs,threshold", [(5, 0.9), (20, 1.3)])
def test_pipeline_batch_average(tmp_path, num_jobs, threshold):
    create_job, pipeline, _ = build_pipeline(tmp_path)
    durations = [duration for _, duration in (_run_single_job(create_job, pipeline, tmp_path, idx) for idx in range(num_jobs))]
    avg = sum(durations) / len(durations)
    assert avg <= threshold, f"Média {avg:.4f}s para {num_jobs} jobs acima de {threshold:.2f}s"


@pytest.mark.performance
def test_pipeline_concurrent_p95(tmp_path):
    create_job, pipeline, _ = build_pipeline(tmp_path)

    def worker(index: int) -> float:
        _, duration = _run_single_job(create_job, pipeline, tmp_path, index)
        return duration

    with ThreadPoolExecutor(max_workers=4) as executor:
        durations = list(executor.map(worker, range(8)))

    p95 = statistics.quantiles(durations, n=20)[-1]
    max_p95 = 1.4
    assert p95 <= max_p95, f"P95 {p95:.4f}s acima de {max_p95:.2f}s sob concorrência"
