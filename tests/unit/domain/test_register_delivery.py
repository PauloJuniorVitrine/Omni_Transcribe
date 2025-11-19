from __future__ import annotations

from pathlib import Path

import pytest

from domain.entities.artifact import Artifact
from domain.entities.job import Job
from domain.entities.value_objects import ArtifactType, EngineType, JobStatus
from domain.usecases.register_delivery import RegisterDelivery
from domain.entities.delivery_record import DeliveryRecord


class InMemoryJobRepository:
    def __init__(self, job: Job) -> None:
        self.job = job

    def find_by_id(self, job_id: str) -> Job | None:
        return self.job if self.job.id == job_id else None


class InMemoryArtifactRepository:
    def __init__(self, artifacts) -> None:
        self.artifacts = artifacts

    def list_by_job(self, job_id: str):
        return self.artifacts


class RecordingDeliveryLogger:
    def __init__(self) -> None:
        self.registered = []

    def register(self, job: Job, package_path: Path) -> None:
        self.registered.append((job.id, package_path))


class InMemoryLogRepository:
    def __init__(self) -> None:
        self.entries = []

    def append(self, entry) -> None:  # type: ignore[override]
        self.entries.append(entry)

    def list_by_job(self, job_id: str):
        return [entry for entry in self.entries if getattr(entry, "job_id", None) == job_id]

    def list_recent(self, limit: int = 20):
        return list(reversed(self.entries))[:limit]


class DummyPackageService:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.called = False

    def create_package(self, job: Job, artifacts):
        self.called = True
        return self.path


class DummyDeliveryClient:
    def __init__(self) -> None:
        self.calls = []

    def submit_package(self, job: Job, package_path: Path) -> DeliveryRecord:
        self.calls.append((job.id, package_path))
        return DeliveryRecord(
            job_id=job.id,
            integration="gotranscript",
            status="submitted",
            external_id="ext-123",
        )


def test_register_delivery_submits_external_and_logs(tmp_path):
    job = Job(
        id="job-1",
        source_path=tmp_path / "audio.wav",
        profile_id="geral",
        status=JobStatus.APPROVED,
        engine=EngineType.OPENAI,
    )
    artifact = Artifact(
        id="art-1",
        job_id=job.id,
        artifact_type=ArtifactType.TRANSCRIPT_TXT,
        path=tmp_path / "file.txt",
    )
    artifact.path.write_text("conteudo", encoding="utf-8")

    job_repo = InMemoryJobRepository(job)
    artifact_repo = InMemoryArtifactRepository([artifact])
    logger = RecordingDeliveryLogger()
    log_repo = InMemoryLogRepository()
    package_service = DummyPackageService(tmp_path / "packages" / "job.zip")
    delivery_client = DummyDeliveryClient()

    use_case = RegisterDelivery(
        job_repository=job_repo,
        artifact_repository=artifact_repo,
        package_service=package_service,
        delivery_logger=logger,
        log_repository=log_repo,
        delivery_client=delivery_client,
    )

    package_path = use_case.execute(job.id)

    assert package_service.called
    assert delivery_client.calls == [(job.id, package_path)]
    assert any(entry.event == "delivery_external_submitted" for entry in log_repo.entries)


def test_register_delivery_requires_approved_job(tmp_path):
    job = Job(
        id="job-pending",
        source_path=tmp_path / "audio.wav",
        profile_id="geral",
        status=JobStatus.PENDING,
        engine=EngineType.OPENAI,
    )
    artifact = Artifact(
        id="art-2",
        job_id=job.id,
        artifact_type=ArtifactType.TRANSCRIPT_TXT,
        path=tmp_path / "file.txt",
    )
    artifact.path.write_text("conteudo", encoding="utf-8")

    use_case = RegisterDelivery(
        job_repository=InMemoryJobRepository(job),
        artifact_repository=InMemoryArtifactRepository([artifact]),
        package_service=DummyPackageService(tmp_path / "pkg.zip"),
        delivery_logger=RecordingDeliveryLogger(),
        log_repository=InMemoryLogRepository(),
    )

    with pytest.raises(ValueError):
        use_case.execute(job.id)


def test_register_delivery_requires_artifacts(tmp_path):
    job = Job(
        id="job-no-artifacts",
        source_path=tmp_path / "audio.wav",
        profile_id="geral",
        status=JobStatus.APPROVED,
        engine=EngineType.OPENAI,
    )
    use_case = RegisterDelivery(
        job_repository=InMemoryJobRepository(job),
        artifact_repository=InMemoryArtifactRepository([]),
        package_service=DummyPackageService(tmp_path / "pkg.zip"),
        delivery_logger=RecordingDeliveryLogger(),
        log_repository=InMemoryLogRepository(),
    )

    with pytest.raises(ValueError):
        use_case.execute(job.id)


def test_register_delivery_enforces_existing_job(tmp_path):
    class EmptyRepo:
        def find_by_id(self, job_id: str):
            return None

    use_case = RegisterDelivery(
        job_repository=EmptyRepo(),
        artifact_repository=InMemoryArtifactRepository([]),
        package_service=DummyPackageService(tmp_path / "pkg.zip"),
        delivery_logger=RecordingDeliveryLogger(),
        log_repository=InMemoryLogRepository(),
    )

    with pytest.raises(ValueError):
        use_case.execute("missing")
