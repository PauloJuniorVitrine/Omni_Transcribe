from __future__ import annotations

import time
from pathlib import Path

from application.services.artifact_builder import FilesystemArtifactBuilder
from application.services.subtitle_formatter import SubtitleFormatter
from application.services.validator_service import TranscriptValidator
from application.services.rejected_logger import FilesystemRejectedLogger
from application.services.sheet_service import CsvSheetService
from application.services.status_publisher import SheetStatusPublisher
from domain.entities.job import Job
from domain.entities.profile import Profile
from domain.entities.value_objects import EngineType
from domain.usecases.create_job import CreateJobFromInbox, CreateJobInput
from domain.usecases.generate_artifacts import GenerateArtifacts
from domain.usecases.pipeline import ProcessJobPipeline
from domain.usecases.post_edit import PostEditTranscript
from domain.usecases.retry_or_reject import RetryOrRejectJob
from domain.usecases.run_asr import RunAsrPipeline
from infrastructure.database.profile_provider import FilesystemProfileProvider
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


def test_pipeline_average_execution_time(tmp_path):
    create_job, pipeline, job_repo = build_pipeline(tmp_path)
    audio_file = tmp_path / "audio.wav"
    audio_file.write_bytes(b"fake audio")

    runs = 5
    durations = []
    for _ in range(runs):
        job = create_job.execute(CreateJobInput(source_path=audio_file, engine=EngineType.OPENAI))
        start = time.perf_counter()
        pipeline.execute(job.id)
        durations.append(time.perf_counter() - start)

    avg = sum(durations) / runs
    max_allowed = 0.6  # relaxado para ambientes sem otimizações nativas
    assert avg < max_allowed, f"Pipeline médio {avg:.4f}s excedeu limite {max_allowed}s"
    # sanity check: artifacts exist
    stored_job = job_repo.find_by_id(job.id)
    assert stored_job and stored_job.status.value == "awaiting_review"
