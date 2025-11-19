from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace

from domain.entities.job import Job
from domain.entities.value_objects import EngineType, JobStatus
from infrastructure.api.gotranscript_client import GoTranscriptClient
from infrastructure.api.storage_client import LocalStorageClient, S3StorageClient


def _make_job(tmp_path: Path, metadata: dict | None = None) -> Job:
    return Job(
        id="job-123",
        source_path=tmp_path / "audio.wav",
        profile_id="default",
        engine=EngineType.OPENAI,
        status=JobStatus.APPROVED,
        metadata=metadata or {},
    )


def test_gotranscript_client_submit_package_sends_payload(tmp_path):
    package_path = tmp_path / "pkg.zip"
    package_path.write_bytes(b"zip-data")
    job = _make_job(tmp_path, metadata={"accuracy_score": "0.98"})
    client = GoTranscriptClient(base_url="https://api.gotranscript.test/v1", api_key="key-123", timeout=10)
    captured: dict = {}

    class DummyResponse:
        def raise_for_status(self) -> None:
            captured["raised"] = True

        def json(self) -> dict:
            return {"delivery_id": "ext-777", "status": "submitted"}

    def fake_post(url, headers, data, files, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["data"] = data
        captured["files"] = files
        captured["timeout"] = timeout
        return DummyResponse()

    client.session.post = fake_post  # type: ignore[assignment]
    record = client.submit_package(job, package_path)

    assert captured["url"].endswith("/deliveries")
    assert captured["headers"]["Authorization"] == "Bearer key-123"
    assert captured["data"]["job_id"] == "job-123"
    assert captured["data"]["meta[accuracy_score]"] == "0.98"
    assert captured["files"]["package"][0] == "pkg.zip"
    assert captured["timeout"] == 10
    assert record.external_id == "ext-777"
    assert record.integration == "gotranscript"


def test_local_storage_client_uploads_file(tmp_path):
    base_dir = tmp_path / "backup"
    client = LocalStorageClient(base_dir)
    source = tmp_path / "file.txt"
    source.write_text("content", encoding="utf-8")

    destination = client.upload(source, "jobs/file.txt")

    assert Path(destination).exists()
    assert Path(destination).read_text(encoding="utf-8") == "content"


def test_s3_storage_client_uploads_with_prefix(tmp_path, monkeypatch):
    uploads: dict = {}

    def fake_client(name, **kwargs):
        uploads["kwargs"] = kwargs

        class FakeClient:
            def upload_file(self, filename, bucket, key):
                uploads["call"] = (filename, bucket, key)

        fake = FakeClient()
        uploads["client"] = fake
        return fake

    monkeypatch.setitem(sys.modules, "boto3", SimpleNamespace(client=fake_client))
    client = S3StorageClient(
        bucket="transcribe",
        prefix="artifacts",
        endpoint_url="http://localhost:9000",
        access_key="a",
        secret_key="b",
        region="us-east-1",
    )
    source = tmp_path / "artifact.zip"
    source.write_bytes(b"data")

    remote = client.upload(source, "job-123/output.zip")

    assert uploads["kwargs"]["endpoint_url"] == "http://localhost:9000"
    assert uploads["kwargs"]["region_name"] == "us-east-1"
    assert uploads["kwargs"]["aws_access_key_id"] == "a"
    assert uploads["call"][1] == "transcribe"
    assert uploads["call"][2] == "artifacts/job-123/output.zip"
    assert remote.endswith("/artifacts/job-123/output.zip")
