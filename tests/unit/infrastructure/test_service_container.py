from __future__ import annotations

from pathlib import Path
import os
from types import SimpleNamespace

os.environ.setdefault("CREDENTIALS_SECRET_KEY", "eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHg=")

from domain.entities.job import Job
from domain.entities.value_objects import EngineType, JobStatus
from infrastructure.container.service_container import ServiceContainer


def _make_container(profiles_dir: Path) -> ServiceContainer:
    container = ServiceContainer.__new__(ServiceContainer)
    container.settings = SimpleNamespace(profiles_dir=profiles_dir)
    container._reference_cache = {}
    return container


def _make_job(tmp_path: Path, profile_id: str = "default", metadata: dict | None = None) -> Job:
    return Job(
        id="job-1",
        source_path=tmp_path / "audio.wav",
        profile_id=profile_id,
        engine=EngineType.OPENAI,
        status=JobStatus.PENDING,
        metadata=metadata or {},
    )


def test_load_reference_prefers_inline_metadata(tmp_path):
    container = _make_container(tmp_path)
    job = _make_job(tmp_path, metadata={"reference_transcript": "Conteudo inline"})

    assert container._load_reference_transcript(job) == "Conteudo inline"


def test_load_reference_from_file_and_cache(tmp_path):
    container = _make_container(tmp_path)
    reference_file = tmp_path / "client.txt"
    reference_file.write_text("arquivo", encoding="utf-8")
    job = _make_job(tmp_path, metadata={"reference_path": str(reference_file)})

    assert container._load_reference_transcript(job) == "arquivo"


def test_load_reference_falls_back_to_profile_cache(tmp_path):
    profiles_dir = tmp_path / "profiles"
    references_dir = profiles_dir / "references"
    references_dir.mkdir(parents=True)
    (references_dir / "finance.txt").write_text("conteudo", encoding="utf-8")
    container = _make_container(profiles_dir)
    job_first = _make_job(tmp_path, profile_id="finance")

    first = container._load_reference_transcript(job_first)
    assert first == "conteudo"

    (references_dir / "finance.txt").unlink()
    job_second = _make_job(tmp_path, profile_id="finance")

    second = container._load_reference_transcript(job_second)
    assert second == "conteudo"
