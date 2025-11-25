from __future__ import annotations

from pathlib import Path

from application.services.artifact_builder import FilesystemArtifactBuilder
from application.services.subtitle_formatter import SubtitleFormatter
from application.services.validator_service import TranscriptValidator
from application.services.sheet_service import CsvSheetService
from domain.entities.job import Job
from domain.entities.profile import Profile
from domain.entities.transcription import PostEditResult, Segment
from domain.entities.value_objects import ArtifactType, EngineType, JobStatus


def make_profile(tmp_path: Path) -> Profile:
    return Profile(
        id="geral",
        meta={"subtitle": {"max_chars_per_line": 80, "max_lines": 2, "reading_speed_cps": 18}},
        prompt_body="dummy",
        source_path=str(tmp_path),
    )


def make_job() -> Job:
    return Job(
        id="job-artifacts",
        source_path=Path("inbox/sample.wav"),
        profile_id="geral",
        status=JobStatus.AWAITING_REVIEW,
        engine=EngineType.OPENAI,
    )


def make_post_edit() -> PostEditResult:
    return PostEditResult(
        text="texto final",
        segments=[Segment(id=0, start=0.0, end=1.0, text="texto final", speaker=None)],
        flags=[],
        language="pt-BR",
    )


def test_filesystem_artifact_builder_creates_files(tmp_path: Path):
    builder = FilesystemArtifactBuilder(
        output_dir=tmp_path / "output",
        subtitle_formatter=SubtitleFormatter(),
        validator=TranscriptValidator(),
    )
    job = make_job()
    profile = make_profile(tmp_path)
    post_edit = make_post_edit()

    artifacts = list(builder.build(job, profile, post_edit))
    assert artifacts
    assert all((artifact.path.exists() for artifact in artifacts))
    assert artifacts[0].artifact_type == ArtifactType.TRANSCRIPT_TXT


def test_csv_sheet_service_records(tmp_path: Path):
    sheet = CsvSheetService(tmp_path / "log.csv", sheet_gateway=None)
    job = make_job()
    job.language = "pt-BR"
    job.duration_sec = 45.0
    package = tmp_path / "pkg.zip"
    package.write_bytes(b"zip")

    sheet.register(job, package)
    content = (tmp_path / "log.csv").read_text()
    assert "job-artifacts" in content
