from __future__ import annotations

import statistics
import time
from pathlib import Path

import pytest

from application.services.artifact_builder import FilesystemArtifactBuilder
from application.services.rejected_logger import FilesystemRejectedLogger
from application.services.sheet_service import CsvSheetService
from application.services.status_publisher import SheetStatusPublisher
from application.services.subtitle_formatter import SubtitleFormatter
from application.services.validator_service import TranscriptValidator
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
    sheet_service = CsvSheetService(tmp_path / "perf_log_ext.csv")
    status_publisher = SheetStatusPublisher(sheet_service)
    rejected_logger = FilesystemRejectedLogger(tmp_path / "rejected_ext")

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
    builder = FilesystemArtifactBuilder(tmp_path / "output_ext", SubtitleFormatter(), TranscriptValidator())
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


@pytest.mark.parametrize("users", [10, 30, 60])
def test_pipeline_throughput_under_burst(tmp_path, users):
    create_job, pipeline, job_repo = build_pipeline(tmp_path)
    audio_file = tmp_path / "audio.wav"
    audio_file.write_bytes(b"fake audio")

    durations = []
    for _ in range(users):
        job = create_job.execute(CreateJobInput(source_path=audio_file, engine=EngineType.OPENAI))
        start = time.perf_counter()
        pipeline.execute(job.id)
        durations.append(time.perf_counter() - start)

    throughput = len(durations) / sum(durations)
    assert throughput >= 1, f"throughput {throughput:.2f} jobs/s ficou abaixo do mínimo com {users} jobs"

    statuses = [job_repo.find_by_id(job_id) for job_id in job_repo.jobs.keys()]
    assert all(job and job.status.value == "awaiting_review" for job in statuses)


def test_pipeline_warns_when_latency_regresses(tmp_path, monkeypatch):
    create_job, pipeline, _ = build_pipeline(tmp_path)
    audio_file = tmp_path / "audio_slow.wav"
    audio_file.write_bytes(b"fake audio")

    slow_calls = {"count": 0}
    original_run = pipeline.asr_use_case.asr_service.run

    def slow_run(job, profile, task="transcribe"):
        slow_calls["count"] += 1
        time.sleep(0.05)
        return original_run(job, profile, task=task)

    monkeypatch.setattr(pipeline.asr_use_case.asr_service, "run", slow_run)

    durations = []
    for _ in range(5):
        job = create_job.execute(CreateJobInput(source_path=audio_file, engine=EngineType.OPENAI))
        start = time.perf_counter()
        pipeline.execute(job.id)
        durations.append(time.perf_counter() - start)

    p95 = statistics.quantiles(sorted(durations), n=20)[-1]
    with pytest.raises(AssertionError):
        assert p95 < 0.02, "deveria falhar quando o pipeline degrada além de 20ms"
    assert p95 >= 0.02
    assert slow_calls["count"] == 5
