from __future__ import annotations

"""
Smoke leve do pipeline com stubs (sem chamadas externas).
Executa create_job -> pipeline -> gera artefatos em diretório temporário
para validar wiring antes do build/installer.
"""

import os
import tempfile
from pathlib import Path

from application.services.artifact_builder import FilesystemArtifactBuilder
from application.services.subtitle_formatter import SubtitleFormatter
from application.services.validator_service import TranscriptValidator
from application.services.rejected_logger import FilesystemRejectedLogger
from application.services.sheet_service import CsvSheetService
from application.services.status_publisher import SheetStatusPublisher
from domain.entities.value_objects import EngineType
from domain.usecases.create_job import CreateJobFromInbox, CreateJobInput
from domain.usecases.generate_artifacts import GenerateArtifacts
from domain.usecases.pipeline import ProcessJobPipeline
from domain.usecases.post_edit import PostEditTranscript
from domain.usecases.retry_or_reject import RetryOrRejectJob
from domain.usecases.run_asr import RunAsrPipeline
from infrastructure.database.profile_provider import FilesystemProfileProvider
from tests.support import stubs


def run_smoke() -> None:
    os.environ.setdefault("TEST_MODE", "1")
    os.environ.setdefault("OMNI_TEST_MODE", "1")
    os.environ.setdefault("SKIP_RUNTIME_CREDENTIALS_VERIFY", "1")

    tmp_root = Path(tempfile.mkdtemp(prefix="smoke_pipeline_"))
    output_dir = tmp_root / "output"
    log_path = tmp_root / "perf_log.csv"
    rejected_dir = tmp_root / "rejected"
    audio_file = tmp_root / "audio.wav"
    audio_file.write_bytes(b"fake audio")

    job_repo = stubs.MemoryJobRepository()
    artifact_repo = stubs.MemoryArtifactRepository()
    log_repo = stubs.MemoryLogRepository()
    profile_provider = FilesystemProfileProvider(Path("profiles"))
    sheet_service = CsvSheetService(log_path)
    status_publisher = SheetStatusPublisher(sheet_service)
    rejected_logger = FilesystemRejectedLogger(rejected_dir)

    create_job = CreateJobFromInbox(
        job_repository=job_repo,
        profile_provider=profile_provider,
        log_repository=log_repo,
        status_publisher=status_publisher,
    )
    asr = RunAsrPipeline(
        job_repository=job_repo,
        profile_provider=profile_provider,
        asr_service=stubs.StubAsrService("smoke"),
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
    builder = FilesystemArtifactBuilder(output_dir, SubtitleFormatter(), TranscriptValidator())
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

    job = create_job.execute(CreateJobInput(source_path=audio_file, engine=EngineType.OPENAI))
    pipeline.execute(job.id)
    stored_job = job_repo.find_by_id(job.id)
    files = list(output_dir.glob(f"{job.id}_*.*"))

    print(f"[SMOKE] Job {job.id} status={stored_job.status.value if stored_job else 'missing'}")
    print(f"[SMOKE] Artefatos gerados: {[f.name for f in files]}")
    print(f"[SMOKE] Logs registrados: {len(log_repo.list_by_job(job.id))}")
    print(f"[SMOKE] Output dir: {output_dir}")


if __name__ == "__main__":
    run_smoke()
