from __future__ import annotations

import sys
from pathlib import Path

from interfaces.cli import run_job


class StubContainer:
    def __init__(self) -> None:
        self.job_repository = object()
        self.create_job_use_case = object()
        self.pipeline_use_case = object()
        self.retry_use_case = object()
        self.settings = type("Settings", (), {"asr_engine": "openai"})()


class StubJobController:
    last_instance: "StubJobController | None" = None

    def __init__(self, job_repository, create_job_use_case, pipeline_use_case, retry_use_case) -> None:
        self.ingest_calls: list[tuple[Path, str]] = []
        self.process_calls: list[str] = []
        StubJobController.last_instance = self

    def list_jobs(self, limit: int = 20):  # pragma: no cover - not used here
        return []

    def ingest_file(self, path: Path, profile_id: str, engine) -> object:
        job_id = "cli-job"
        self.ingest_calls.append((path, profile_id))
        return type("Job", (), {"id": job_id})

    def process_job(self, job_id: str) -> None:
        self.process_calls.append(job_id)


def test_cli_run_job_processes_file(monkeypatch, tmp_path):
    audio_path = tmp_path / "audio.wav"
    audio_path.write_bytes(b"x")

    monkeypatch.setattr(run_job, "get_container", lambda: StubContainer())
    monkeypatch.setattr(run_job, "JobController", StubJobController)
    monkeypatch.setattr(sys, "argv", ["run_job.py", "--file", str(audio_path), "--profile", "geral", "--engine", "local"])

    run_job.main()

    controller = StubJobController.last_instance
    assert controller is not None
    assert controller.ingest_calls == [(audio_path, "geral")]
    assert controller.process_calls == ["cli-job"]
