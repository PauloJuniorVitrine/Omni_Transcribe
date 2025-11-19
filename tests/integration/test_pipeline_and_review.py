from __future__ import annotations

import csv
from pathlib import Path

import pytest

from application.controllers.review_controller import ReviewController
from application.services.artifact_builder import FilesystemArtifactBuilder
from application.services.package_service import ZipPackageService
from application.services.sheet_service import CsvSheetService
from application.services.rejected_logger import FilesystemRejectedLogger
from application.services.subtitle_formatter import SubtitleFormatter
from application.services.validator_service import TranscriptValidator
from domain.entities.artifact import Artifact
from domain.entities.job import Job
from domain.entities.profile import Profile
from domain.entities.transcription import PostEditResult, Segment, TranscriptionResult
from domain.entities.value_objects import ArtifactType, EngineType, JobStatus, LogLevel
from domain.usecases.generate_artifacts import GenerateArtifacts
from domain.usecases.handle_review import HandleReviewDecision
from domain.usecases.pipeline import ProcessJobPipeline
from domain.usecases.post_edit import PostEditTranscript
from domain.usecases.register_delivery import RegisterDelivery
from domain.usecases.retry_or_reject import RetryDecision, RetryOrRejectJob
from domain.usecases.run_asr import RunAsrPipeline


class InMemoryJobRepository:
    def __init__(self, job: Job) -> None:
        self.job = job

    def create(self, job: Job) -> Job:
        self.job = job
        return job

    def update(self, job: Job) -> Job:
        self.job = job
        return job

    def find_by_id(self, job_id: str) -> Job | None:
        return self.job if self.job.id == job_id else None

    def list_recent(self, limit: int = 50):
        return [self.job]


class InMemoryArtifactRepository:
    def __init__(self) -> None:
        self.items: list[Artifact] = []

    def save_many(self, artifacts):
        self.items.extend(artifacts)

    def list_by_job(self, job_id: str):
        return [artifact for artifact in self.items if artifact.job_id == job_id]


class InMemoryLogRepository:
    def __init__(self) -> None:
        self.entries: list[tuple[str, LogLevel]] = []

    def append(self, entry) -> None:  # type: ignore[override]
        self.entries.append((entry.event, entry.level))

    def list_by_job(self, job_id: str):
        return [entry for entry in self.entries if entry[0] == job_id]

    def list_recent(self, limit: int = 20):
        return []


class StubProfileProvider:
    def __init__(self, profile: Profile) -> None:
        self.profile = profile

    def get(self, profile_id: str) -> Profile:
        return self.profile


class StubAsrService:
    def run(self, job: Job, profile: Profile, task: str = "transcribe") -> TranscriptionResult:
        return TranscriptionResult(
            text="ola mundo",
            segments=[Segment(id=0, start=0.0, end=2.0, text="olá mundo")],
            language="pt",
            duration_sec=2.0,
            engine=job.engine.value,
            metadata={"task": task},
        )


class FailingAsrService(StubAsrService):
    def run(self, job: Job, profile: Profile, task: str = "transcribe") -> TranscriptionResult:  # type: ignore[override]
        raise RuntimeError("asr indisponível")


class FailingArtifactBuilder:
    def build(self, job: Job, profile: Profile, post_edit_result: PostEditResult):
        raise RuntimeError("erro ao gravar artefatos")


class StubPostEditService:
    def run(self, job: Job, profile: Profile, transcription: TranscriptionResult) -> PostEditResult:
        return PostEditResult(
            text=transcription.text.upper(),
            segments=transcription.segments,
            flags=[],
            language=transcription.language,
        )


class InMemoryReviewRepository:
    def __init__(self) -> None:
        self.saved = []

    def save(self, review):
        self.saved.append(review)
        return review

    def find_latest(self, job_id: str):
        return next((item for item in reversed(self.saved) if item.job_id == job_id), None)


def build_profile() -> Profile:
    return Profile(
        id="geral",
        meta={
            "subtitle": {"max_chars_per_line": 32, "max_lines": 2, "reading_speed_cps": 18},
            "disclaimers": ["Exige revisão humana"],
        },
        prompt_body="body",
    )


def test_pipeline_generates_artifacts_and_updates_job(tmp_path: Path) -> None:
    job = Job(
        id="job-pipeline",
        source_path=tmp_path / "audio.wav",
        profile_id="geral",
        engine=EngineType.OPENAI,
    )
    repo = InMemoryJobRepository(job)
    artifact_repo = InMemoryArtifactRepository()
    log_repo = InMemoryLogRepository()
    profile_provider = StubProfileProvider(build_profile())

    run_asr = RunAsrPipeline(repo, profile_provider, StubAsrService(), log_repo)
    post_edit = PostEditTranscript(repo, profile_provider, StubPostEditService(), log_repo)
    builder = FilesystemArtifactBuilder(tmp_path / "output", SubtitleFormatter(), TranscriptValidator())
    generate_artifacts = GenerateArtifacts(repo, artifact_repo, builder, log_repo, profile_provider)
    rejected_logger = FilesystemRejectedLogger(tmp_path / "rejected")
    retry = RetryOrRejectJob(repo, log_repo, rejected_logger)
    pipeline = ProcessJobPipeline(run_asr, post_edit, generate_artifacts, log_repo, retry_handler=retry)

    artifacts = pipeline.execute(job.id)

    assert repo.job.status == JobStatus.AWAITING_REVIEW
    assert len(artifacts) == 4
    assert (tmp_path / "output" / job.id / f"{job.id}_v1.txt").exists()
    assert ("asr_completed", LogLevel.INFO) in log_repo.entries
    assert artifact_repo.list_by_job(job.id)


def test_review_controller_approves_and_creates_package(tmp_path: Path) -> None:
    job = Job(
        id="job-review",
        source_path=tmp_path / "audio.wav",
        profile_id="geral",
        engine=EngineType.OPENAI,
        status=JobStatus.AWAITING_REVIEW,
    )
    repo = InMemoryJobRepository(job)
    log_repo = InMemoryLogRepository()
    artifact_repo = InMemoryArtifactRepository()
    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir()
    for suffix in (".txt", ".json"):
        file_path = artifact_dir / f"{job.id}{suffix}"
        file_path.write_text("conteudo", encoding="utf-8")
        artifact_repo.items.append(
            Artifact(
                id=f"a{suffix}",
                job_id=job.id,
                artifact_type=ArtifactType.TRANSCRIPT_TXT if suffix == ".txt" else ArtifactType.STRUCTURED_JSON,
                path=file_path,
                version=1,
            )
        )

    sheet_service = CsvSheetService(tmp_path / "log.csv")
    package_service = ZipPackageService(tmp_path / "backup")
    register_delivery = RegisterDelivery(repo, artifact_repo, package_service, sheet_service, log_repo)
    review_use_case = HandleReviewDecision(repo, InMemoryReviewRepository(), log_repo)
    controller = ReviewController(repo, review_use_case, sheet_service, register_delivery)

    controller.submit_review(job.id, reviewer="Ana", approved=True, notes="ok")

    assert repo.job.status == JobStatus.APPROVED
    backup_zip = tmp_path / "backup" / job.id / f"{job.id}_v1.zip"
    assert backup_zip.exists()

    with open(sheet_service.csv_path, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
        assert any(row["job_id"] == job.id and row["status"] == JobStatus.APPROVED.value for row in rows)


def test_pipeline_failure_creates_rejected_log(tmp_path: Path) -> None:
    job = Job(
        id="job-fail",
        source_path=tmp_path / "audio.wav",
        profile_id="geral",
        engine=EngineType.OPENAI,
    )
    repo = InMemoryJobRepository(job)
    artifact_repo = InMemoryArtifactRepository()
    log_repo = InMemoryLogRepository()
    profile_provider = StubProfileProvider(build_profile())

    run_asr = RunAsrPipeline(repo, profile_provider, FailingAsrService(), log_repo)
    post_edit = PostEditTranscript(repo, profile_provider, StubPostEditService(), log_repo)
    builder = FilesystemArtifactBuilder(tmp_path / "output", SubtitleFormatter(), TranscriptValidator())
    generate_artifacts = GenerateArtifacts(repo, artifact_repo, builder, log_repo, profile_provider)
    rejected_logger = FilesystemRejectedLogger(tmp_path / "rejected")
    retry = RetryOrRejectJob(repo, log_repo, rejected_logger)
    pipeline = ProcessJobPipeline(run_asr, post_edit, generate_artifacts, log_repo, retry_handler=retry)

    try:
        pipeline.execute(job.id)
    except RuntimeError:
        pass

    files = list((tmp_path / "rejected" / job.id).glob("failure_*.json"))
    assert files
    body = files[0].read_text(encoding="utf-8")
    assert '"stage": "asr"' in body
    assert "asr indisponível" in body


def test_pipeline_artifact_failure_marks_stage(tmp_path: Path) -> None:
    job = Job(
        id="job-artifact-fail",
        source_path=tmp_path / "audio.wav",
        profile_id="geral",
        engine=EngineType.OPENAI,
    )
    repo = InMemoryJobRepository(job)
    artifact_repo = InMemoryArtifactRepository()
    log_repo = InMemoryLogRepository()
    profile_provider = StubProfileProvider(build_profile())

    run_asr = RunAsrPipeline(repo, profile_provider, StubAsrService(), log_repo)
    post_edit = PostEditTranscript(repo, profile_provider, StubPostEditService(), log_repo)
    builder = FailingArtifactBuilder()
    generate_artifacts = GenerateArtifacts(repo, artifact_repo, builder, log_repo, profile_provider)
    rejected_logger = FilesystemRejectedLogger(tmp_path / "rejected")
    retry = RetryOrRejectJob(repo, log_repo, rejected_logger)
    pipeline = ProcessJobPipeline(run_asr, post_edit, generate_artifacts, log_repo, retry_handler=retry)

    with pytest.raises(RuntimeError):
        pipeline.execute(job.id)

    files = list((tmp_path / "rejected" / job.id).glob("failure_*.json"))
    assert files
    body = files[0].read_text(encoding="utf-8")
    assert '"stage": "artifacts"' in body
    assert "erro ao gravar artefatos" in body
