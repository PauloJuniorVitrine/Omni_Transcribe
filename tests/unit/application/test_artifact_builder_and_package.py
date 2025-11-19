from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZipFile

from application.services.artifact_builder import FilesystemArtifactBuilder
from application.services.package_service import ZipPackageService
from application.services.subtitle_formatter import SubtitleFormatter
from application.services.validator_service import TranscriptValidator
from domain.entities.artifact import Artifact
from domain.entities.job import Job
from domain.entities.profile import Profile
from domain.entities.transcription import PostEditResult, Segment
from domain.entities.value_objects import ArtifactType
from domain.ports.services import StorageClient


def make_job(job_id: str, tmp_path: Path) -> Job:
    return Job(id=job_id, source_path=tmp_path / f"{job_id}.wav", profile_id="geral", version=2)


def make_profile() -> Profile:
    return Profile(
        id="geral",
        meta={
            "disclaimers": ["Uso restrito"],
            "subtitle": {"max_chars_per_line": 40, "max_lines": 2, "reading_speed_cps": 20},
        },
        prompt_body="body",
    )


def make_post_edit_result() -> PostEditResult:
    return PostEditResult(
        text="Linha 1. Linha 2.",
        segments=[Segment(id=0, start=0.0, end=2.0, text="Linha extensa demais para caber em uma só linha")],
        flags=[{"type": "warning", "message": "algo"}],
        language="pt",
    )


def test_filesystem_artifact_builder_generates_all_formats(tmp_path: Path) -> None:
    builder = FilesystemArtifactBuilder(tmp_path, SubtitleFormatter(), TranscriptValidator())
    job = make_job("job123", tmp_path)
    profile = make_profile()
    post_edit = make_post_edit_result()

    artifacts = list(builder.build(job, profile, post_edit))
    artifact_types = {artifact.artifact_type for artifact in artifacts}

    assert artifact_types == {
        ArtifactType.TRANSCRIPT_TXT,
        ArtifactType.SUBTITLE_SRT,
        ArtifactType.SUBTITLE_VTT,
        ArtifactType.STRUCTURED_JSON,
    }

    txt_file = tmp_path / job.id / f"{job.id}_v{job.version}.txt"
    assert "Uso restrito" in txt_file.read_text(encoding="utf-8")

    json_file = tmp_path / job.id / f"{job.id}_v{job.version}.json"
    payload = json.loads(json_file.read_text(encoding="utf-8"))
    assert payload["flags"] == [{"type": "warning", "message": "algo"}]
    assert payload["warnings"]  # validator populates warnings due a long line


class StubStorageClient(StorageClient):
    def __init__(self) -> None:
        self.uploads: list[tuple[Path, str]] = []

    def upload(self, local_path: Path, remote_key: str) -> str:
        self.uploads.append((local_path, remote_key))
        return f"s3://bucket/{remote_key}"


def test_zip_package_service_creates_zip_and_uploads(tmp_path: Path) -> None:
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    artifact_files = []
    for suffix in (".txt", ".srt"):
        file_path = artifacts_dir / f"job123{suffix}"
        file_path.write_text(f"conteudo {suffix}", encoding="utf-8")
        artifact_files.append(
            Artifact(
                id=f"a{suffix}",
                job_id="job123",
                artifact_type=ArtifactType.TRANSCRIPT_TXT if suffix == ".txt" else ArtifactType.SUBTITLE_SRT,
                path=file_path,
                version=1,
            )
        )

    job = make_job("job123", tmp_path)
    storage = StubStorageClient()
    service = ZipPackageService(tmp_path / "backup", storage_client=storage)

    package_path = service.create_package(job, artifact_files)
    assert package_path.exists()
    with ZipFile(package_path) as zip_file:
        names = zip_file.namelist()
        assert any(name.endswith(".txt") for name in names)
        assert any(name.endswith(".srt") for name in names)

    assert storage.uploads == [(package_path, f"{job.id}/{package_path.name}")]
