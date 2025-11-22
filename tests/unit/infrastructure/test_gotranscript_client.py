from __future__ import annotations

import types

import pytest

from infrastructure.api.gotranscript_client import GoTranscriptClient
from domain.entities.job import Job
from domain.entities.value_objects import EngineType, JobStatus


class _StubResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self) -> dict:
        return self._payload


def _job(tmp_path):
    audio = tmp_path / "a.wav"
    audio.write_text("audio", encoding="utf-8")
    return Job(id="j1", source_path=audio, profile_id="p", engine=EngineType.OPENAI, status=JobStatus.APPROVED)


def test_submit_package_success(monkeypatch, tmp_path):
    captured = {}

    def fake_post(url, headers, data, files, timeout):  # noqa: ANN001
        captured["url"] = url
        captured["headers"] = headers
        captured["data"] = data
        captured["files"] = files
        captured["timeout"] = timeout
        return _StubResponse({"id": "ext-1", "status": "submitted"})

    session = types.SimpleNamespace(post=fake_post)
    client = GoTranscriptClient(base_url="https://api.example", api_key="k", timeout=10)
    client.session = session  # override real session
    job = _job(tmp_path)
    pkg = tmp_path / "pkg.zip"
    pkg.write_text("zip", encoding="utf-8")

    record = client.submit_package(job, pkg)

    assert captured["url"].endswith("/deliveries")
    assert "Authorization" in captured["headers"]
    assert captured["data"]["job_id"] == job.id
    assert record.external_id == "ext-1"
    assert record.status == "submitted"


def test_submit_package_error_raises(monkeypatch, tmp_path):
    client = GoTranscriptClient(base_url="https://api.example", api_key="k", timeout=10)
    client.session = types.SimpleNamespace(post=lambda *args, **kwargs: _StubResponse({}, status_code=500))
    job = _job(tmp_path)
    pkg = tmp_path / "pkg.zip"
    pkg.write_text("zip", encoding="utf-8")

    with pytest.raises(RuntimeError):
        client.submit_package(job, pkg)
