from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

from application.services.package_service import ZipPackageService
from domain.entities.artifact import Artifact
from domain.entities.job import Job
from domain.entities.value_objects import ArtifactType, EngineType, JobStatus


class _StubStorage:
    def __init__(self) -> None:
        self.uploaded: list[tuple[Path, str]] = []

    def upload(self, local_path: Path, remote_key: str) -> str:
        self.uploaded.append((local_path, remote_key))
        return f"s3://bucket/{remote_key}"


def test_zip_package_writes_files_and_calls_storage(tmp_path):
    backup_dir = tmp_path / "backup"
    storage = _StubStorage()
    service = ZipPackageService(backup_dir, storage_client=storage)

    audio = tmp_path / "audio.wav"
    audio.write_text("audio", encoding="utf-8")
    job = Job(
        id="job-zip",
        source_path=audio,
        profile_id="p",
        engine=EngineType.OPENAI,
        status=JobStatus.APPROVED,
    )
    art_dir = tmp_path / "output"
    art_dir.mkdir()
    artifact_path = art_dir / "job-zip_v1.txt"
    artifact_path.write_text("hello", encoding="utf-8")
    artifacts = [
        Artifact(id="a1", job_id=job.id, artifact_type=ArtifactType.TRANSCRIPT_TXT, path=artifact_path, version=1),
    ]

    package = service.create_package(job, artifacts)

    assert package.exists()
    with ZipFile(package) as zf:
        names = zf.namelist()
        assert names == [f"{job.id}/{artifact_path.name}"]
    assert storage.uploaded
    uploaded_path, remote_key = storage.uploaded[0]
    assert uploaded_path == package
    assert remote_key == f"{job.id}/{package.name}"
