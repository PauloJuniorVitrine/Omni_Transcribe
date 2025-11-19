from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from domain.entities.job import Job
from domain.entities.value_objects import EngineType, JobStatus


class DummyController:
    def __init__(self, job_repository, create_job_use_case, pipeline_use_case, retry_use_case):
        self.job_repository = job_repository
        self.create_job_use_case = create_job_use_case
        self.pipeline_use_case = pipeline_use_case
        self.retry_use_case = retry_use_case
        self.ingested = None
        self.processed = []

    def ingest_file(self, path, profile_id, engine):
        self.ingested = (path, profile_id, engine)
        return Job(
            id="job-new",
            source_path=path,
            profile_id=profile_id,
            engine=engine,
            status=JobStatus.PENDING,
        )

    def process_job(self, job_id: str):
        self.processed.append(job_id)


def _run_cli(monkeypatch, args, tmp_path, controller_cls=DummyController):
    from interfaces.cli import run_job
    container = _stub_container()
    monkeypatch.setattr(run_job, "get_container", lambda: container)
    controller_instance = controller_cls(None, None, None, None)
    monkeypatch.setattr(run_job, "JobController", lambda *a, **k: controller_instance)
    monkeypatch.setattr(sys, "argv", ["run_job"] + args)
    run_job.main()
    return controller_instance


def _stub_container():
    return SimpleNamespace(
        job_repository=None,
        create_job_use_case=None,
        pipeline_use_case=None,
        retry_use_case=None,
        settings=SimpleNamespace(asr_engine="openai"),
    )


def test_run_job_requires_job_id_or_file(monkeypatch, tmp_path):
    from interfaces.cli import run_job
    container = _stub_container()
    monkeypatch.setattr(run_job, "get_container", lambda: container)
    monkeypatch.setattr(run_job, "JobController", lambda *a, **k: DummyController(None, None, None, None))
    monkeypatch.setattr(sys, "argv", ["run_job"])
    with pytest.raises(SystemExit):
        run_job.main()


def test_run_job_process_existing(monkeypatch, tmp_path):
    controller = _run_cli(monkeypatch, ["--job-id", "job-123"], tmp_path)
    assert controller.processed == ["job-123"]


def test_run_job_ingest_file(monkeypatch, tmp_path):
    audio = tmp_path / "audio.wav"
    audio.write_text("fake", encoding="utf-8")
    controller = _run_cli(monkeypatch, ["--file", str(audio), "--profile", "cliente-x"], tmp_path)
    assert controller.ingested[1] == "cliente-x"
    assert controller.processed == ["job-new"]


def test_run_job_raises_when_file_missing(monkeypatch):
    from interfaces.cli import run_job
    container = _stub_container()
    monkeypatch.setattr(run_job, "get_container", lambda: container)
    monkeypatch.setattr(run_job, "JobController", lambda *a, **k: DummyController(None, None, None, None))
    fake = Path("missing.wav")
    if fake.exists():
        fake.unlink()
    monkeypatch.setattr(sys, "argv", ["run_job", "--file", str(fake)])
    with pytest.raises(SystemExit):
        run_job.main()
