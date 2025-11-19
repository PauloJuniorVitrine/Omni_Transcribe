from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from domain.entities.job import Job
from domain.entities.value_objects import EngineType, JobStatus
from interfaces.cli.watch_inbox import InboxEventHandler, CreateJobInput
from domain.usecases.create_job import CreateJobFromInbox
from domain.usecases.run_asr import RunAsrPipeline
from domain.usecases.post_edit import PostEditTranscript
from domain.usecases.generate_artifacts import GenerateArtifacts
from domain.usecases.retry_or_reject import RetryOrRejectJob
from domain.usecases.pipeline import ProcessJobPipeline
from application.services.artifact_builder import FilesystemArtifactBuilder
from application.services.subtitle_formatter import SubtitleFormatter
from application.services.validator_service import TranscriptValidator
from application.services.sheet_service import CsvSheetService
from application.services.status_publisher import SheetStatusPublisher
from application.services.rejected_logger import FilesystemRejectedLogger
from infrastructure.database.profile_provider import FilesystemProfileProvider
from tests.support.stubs import (
    ImmediateThread,
    MemoryArtifactRepository,
    MemoryJobRepository,
    MemoryLogRepository,
    StubAsrService,
    StubPostEditService,
)


class StubCreateJobUseCase:
    def __init__(self) -> None:
        self.calls: list[CreateJobInput] = []

    def execute(self, data: CreateJobInput) -> Job:
        self.calls.append(data)
        return Job(
            id="job-watcher",
            source_path=data.source_path,
            profile_id=data.profile_id or "geral",
            engine=data.engine,
        )


class StubPipelineUseCase:
    def __init__(self) -> None:
        self.executed: list[str] = []

    def execute(self, job_id: str) -> None:
        self.executed.append(job_id)


class StubContainer:
    def __init__(self, base_input_dir: Path) -> None:
        self.settings = SimpleNamespace(base_input_dir=base_input_dir, asr_engine="openai", max_audio_size_mb=10)
        self.create_job_use_case = StubCreateJobUseCase()
        self.pipeline_use_case = StubPipelineUseCase()


class ImmediateThread:
    def __init__(self, target, args=(), kwargs=None, daemon=None) -> None:
        self.target = target
        self.args = args
        self.kwargs = kwargs or {}

    def start(self) -> None:
        self.target(*self.args, **self.kwargs)


def test_watcher_handles_new_audio(tmp_path, monkeypatch):
    container = StubContainer(tmp_path)
    handler = InboxEventHandler(container)

    monkeypatch.setattr("interfaces.cli.watch_inbox.threading.Thread", ImmediateThread)

    inbox_file = tmp_path / "medico" / "consulta.wav"
    inbox_file.parent.mkdir(parents=True, exist_ok=True)
    inbox_file.write_bytes(b"audio")

    handler._handle_audio(inbox_file)

    assert container.create_job_use_case.calls
    call = container.create_job_use_case.calls[0]
    assert call.source_path == inbox_file
    assert call.profile_id == "medico"
    assert container.pipeline_use_case.executed == ["job-watcher"]


def test_watcher_skips_files_exceeding_limit(tmp_path, monkeypatch):
    container = StubContainer(tmp_path)
    container.settings.max_audio_size_mb = 0  # force limit
    handler = InboxEventHandler(container)

    inbox_file = tmp_path / "geral" / "huge.wav"
    inbox_file.parent.mkdir(parents=True, exist_ok=True)
    inbox_file.write_bytes(b"x" * 10_000)

    handler._handle_audio(inbox_file)

    assert not container.create_job_use_case.calls
    assert not container.pipeline_use_case.executed


class SmokeContainer:
    def __init__(self, base_input_dir: Path, tmp_path: Path) -> None:
        self.settings = SimpleNamespace(base_input_dir=base_input_dir, asr_engine="openai", max_audio_size_mb=1024)
        self.job_repository = MemoryJobRepository()
        self.artifact_repository = MemoryArtifactRepository()
        self.log_repository = MemoryLogRepository()
        self.profile_provider = FilesystemProfileProvider(Path("profiles"))
        self.sheet_service = CsvSheetService(tmp_path / "log.csv")
        self.status_publisher = SheetStatusPublisher(self.sheet_service)
        self.rejected_logger = FilesystemRejectedLogger(tmp_path / "rejected")

        self.create_job_use_case = CreateJobFromInbox(
            job_repository=self.job_repository,
            profile_provider=self.profile_provider,
            log_repository=self.log_repository,
            status_publisher=self.status_publisher,
        )
        self.run_asr_use_case = RunAsrPipeline(
            job_repository=self.job_repository,
            profile_provider=self.profile_provider,
            asr_service=StubAsrService("smoke input"),
            log_repository=self.log_repository,
            status_publisher=self.status_publisher,
        )
        self.post_edit_use_case = PostEditTranscript(
            job_repository=self.job_repository,
            profile_provider=self.profile_provider,
            post_edit_service=StubPostEditService(),
            log_repository=self.log_repository,
            status_publisher=self.status_publisher,
        )

        builder = FilesystemArtifactBuilder(tmp_path / "output", SubtitleFormatter(), TranscriptValidator())
        self.generate_artifacts_use_case = GenerateArtifacts(
            job_repository=self.job_repository,
            artifact_repository=self.artifact_repository,
            artifact_builder=builder,
            log_repository=self.log_repository,
            profile_provider=self.profile_provider,
            status_publisher=self.status_publisher,
        )
        self.retry_use_case = RetryOrRejectJob(
            job_repository=self.job_repository,
            log_repository=self.log_repository,
            rejected_logger=self.rejected_logger,
            status_publisher=self.status_publisher,
        )
        self.pipeline_use_case = ProcessJobPipeline(
            asr_use_case=self.run_asr_use_case,
            post_edit_use_case=self.post_edit_use_case,
            artifact_use_case=self.generate_artifacts_use_case,
            log_repository=self.log_repository,
            retry_handler=self.retry_use_case,
        )


def test_watcher_smoke_pipeline(tmp_path, monkeypatch):
    inbox_dir = tmp_path / "inbox"
    inbox_dir.mkdir()
    container = SmokeContainer(inbox_dir, tmp_path)
    handler = InboxEventHandler(container)
    monkeypatch.setattr("interfaces.cli.watch_inbox.threading.Thread", ImmediateThread)

    audio_file = inbox_dir / "geral" / "audio.wav"
    audio_file.parent.mkdir(parents=True, exist_ok=True)
    audio_file.write_bytes(b"audio")

    handler._handle_audio(audio_file)

    assert container.job_repository.jobs
    stored_job = next(iter(container.job_repository.jobs.values()))
    assert stored_job.status == JobStatus.AWAITING_REVIEW
    output_txt = tmp_path / "output" / stored_job.id / f"{stored_job.id}_v1.txt"
    assert output_txt.exists()
    assert "SMOKE INPUT" in output_txt.read_text(encoding="utf-8")
