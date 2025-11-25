from __future__ import annotations

import hashlib
import hmac
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import interfaces.http.app as http_app
from domain.entities.value_objects import ArtifactType
from domain.entities.job import Job
from domain.entities.log_entry import LogEntry
from domain.entities.value_objects import EngineType, JobStatus, LogLevel


def test_enforce_download_rate_limits_requests(monkeypatch):
    monkeypatch.setenv("TEST_MODE", "0")
    monkeypatch.setenv("OMNI_TEST_MODE", "0")
    http_app._download_tracker.clear()
    monkeypatch.setattr(http_app, "_DOWNLOAD_RATE_LIMIT", 2, raising=False)
    monkeypatch.setattr(http_app, "_DOWNLOAD_RATE_WINDOW_SEC", 3600, raising=False)

    http_app._enforce_download_rate("session-x")
    http_app._enforce_download_rate("session-x")
    with pytest.raises(HTTPException):
        http_app._enforce_download_rate("session-x")


def test_enforce_download_rate_discards_old_entries():
    http_app._download_tracker.clear()
    http_app._download_tracker["anonymous"] = deque([time.time() - 3600])
    http_app._enforce_download_rate(None)
    assert len(http_app._download_tracker["anonymous"]) == 1


def test_validate_download_token_accepts_and_rejects(monkeypatch):
    settings = SimpleNamespace(webhook_secret="secret")
    monkeypatch.setattr(http_app, "get_settings", lambda: settings)
    expires = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
    path = "/output/file.txt"
    payload = f"{path}:{expires}".encode("utf-8")
    token = hmac.new(settings.webhook_secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()

    http_app._validate_download_token(path=path, token=token, expires=expires)

    with pytest.raises(HTTPException):
        http_app._validate_download_token(path=path, token="invalid", expires=expires)


def test_sign_and_validate_upload_token(monkeypatch):
    settings = SimpleNamespace(webhook_secret="secret")
    monkeypatch.setattr(http_app, "get_settings", lambda: settings)
    token, expires = http_app._sign_upload_token(profile="geral", engine="openai", ttl_minutes=1)
    http_app._validate_upload_token(token=token, expires=expires, profile="geral", engine="openai")
    with pytest.raises(HTTPException):
        http_app._validate_upload_token(token="bad", expires=expires, profile="geral", engine="openai")


def test_get_flash_message_and_safe_int():
    message = http_app._get_flash_message("process-started")
    assert message["variant"] == "info"
    assert http_app._get_flash_message(None) is None

    assert http_app._safe_int("5", default=1, minimum=1, maximum=10) == 5
    assert http_app._safe_int("-5", default=1, minimum=1, maximum=10) == 1
    assert http_app._safe_int("999", default=1, minimum=1, maximum=10) == 10
    assert http_app._safe_int("invalid", default=3, maximum=5) == 3


def test_sanitize_upload_filename_normalizes_and_preserves_extension():
    assert http_app._sanitize_upload_filename("Meu Audio.WAV") == "Meu-Audio.wav"
    assert http_app._sanitize_upload_filename("áudio-estranho.mp3") == "audio-estranho.mp3"


def test_sanitize_upload_filename_blocks_traversal_and_invalid_extension():
    with pytest.raises(HTTPException):
        http_app._sanitize_upload_filename("../malicioso.wav")
    with pytest.raises(HTTPException):
        http_app._sanitize_upload_filename("evil.txt")


def test_validate_upload_mime_allows_audio_and_rejects_other():
    http_app._validate_upload_mime("audio/wav")
    http_app._validate_upload_mime("audio/mp3; charset=utf-8")
    with pytest.raises(HTTPException):
        http_app._validate_upload_mime("application/pdf")
    with pytest.raises(HTTPException):
        http_app._validate_upload_mime("text/plain")


def test_enforce_download_rate_scoped_by_session_and_ip(monkeypatch):
    http_app._download_tracker.clear()
    monkeypatch.setattr(http_app, "_DOWNLOAD_RATE_LIMIT", 1, raising=False)
    # Same session+ip blocks second attempt
    http_app._enforce_download_rate("sess:ip1")
    with pytest.raises(HTTPException):
        http_app._enforce_download_rate("sess:ip1")
    # Different IP should not block
    http_app._enforce_download_rate("sess:ip2")


def _make_job(job_id: str, status: JobStatus, profile: str = "default", **metadata) -> Job:
    job = Job(
        id=job_id,
        source_path=Path(f"inbox/{job_id}.wav"),
        profile_id=profile,
        engine=EngineType.OPENAI,
        status=status,
        metadata=metadata or None,
    )
    return job


def test_apply_filters_and_summary_helpers():
    jobs = [
        _make_job("job-1", JobStatus.AWAITING_REVIEW, profile="legal"),
        _make_job("job-2", JobStatus.APPROVED, profile="media", accuracy_requires_review="true"),
        _make_job("job-3", JobStatus.FAILED, profile="legal"),
    ]
    review_filtered = http_app._apply_filters(jobs, status=JobStatus.APPROVED.value, profile=None, accuracy=None)
    assert [job.id for job in review_filtered] == ["job-2"]
    accuracy_filtered = http_app._apply_filters(jobs, status=None, profile=None, accuracy="needs_review")
    assert [job.id for job in accuracy_filtered] == ["job-2"]
    profile_filtered = http_app._apply_filters(jobs, status=None, profile="legal", accuracy=None)
    assert [job.id for job in profile_filtered] == ["job-1", "job-3"]
    passing_filtered = http_app._apply_filters(jobs, status=None, profile=None, accuracy="passing")
    assert "job-2" not in [job.id for job in passing_filtered]

    summary = http_app._compute_summary(jobs)
    assert summary["total"] == 3
    assert summary["awaiting_review"] == 1
    assert summary["failed"] == 1


def test_compute_accuracy_summary_handles_invalid_values():
    jobs = [
        _make_job(
            "job-invalid",
            JobStatus.APPROVED,
            accuracy_score="not-a-number",
            accuracy_wer="bad",
            accuracy_status="custom",
            accuracy_requires_review="false",
        )
    ]
    summary = http_app._compute_accuracy_summary(jobs)
    assert summary["evaluated"] == 1
    assert summary["average_score"] is None
    assert summary["passing"] == 0


def test_compose_accuracy_snapshot_and_format_label():
    metadata = {
        "accuracy_status": "needs_review",
        "accuracy_requires_review": "true",
        "accuracy_score": "0.91",
        "accuracy_baseline": "0.95",
        "accuracy_penalty": "0.04",
        "accuracy_wer": "0.09",
        "accuracy_reference_source": "client_reference",
        "accuracy_updated_at": "2025-11-14T10:00:00Z",
    }
    job = _make_job("job-accuracy", JobStatus.APPROVED, **metadata)
    snapshot = http_app._compose_accuracy_snapshot(job)
    assert snapshot["requires_review"] is True
    assert snapshot["badge"] == "warning"
    assert snapshot["score"] == "91.00%"
    assert snapshot["reference_source"] == "client_reference"

    label = http_app._format_template_label("2025-11-14T10:30:00")
    assert "Atualizado" in label
    assert http_app._format_template_label("invalid-date").startswith("Atualiza")


def test_compose_accuracy_snapshot_handles_custom_status():
    job = _make_job(
        "job-custom",
        JobStatus.APPROVED,
        accuracy_status="custom_state",
        accuracy_score="invalid",
        accuracy_wer="bad",
    )
    snapshot = http_app._compose_accuracy_snapshot(job)
    assert snapshot["badge"] == "info"
    assert snapshot["score"] == "N/A"


def test_load_template_audit_and_incidents(tmp_path, monkeypatch):
    audit_path = tmp_path / "audit.log"
    audit_path.write_text(
        "\n".join(
            [
                '{"timestamp": "2025-11-14T10:00:00Z", "action": "create", "template_id": "a"}',
                "invalid-json",
                '{"timestamp": "2025-11-14T11:00:00Z", "action": "delete", "template_id": "b"}',
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(http_app, "_template_audit_path", audit_path, raising=False)
    entries = http_app._load_template_audit(limit=5)
    assert entries[0]["template_id"] == "b"
    assert entries[1]["template_id"] == "a"
    missing_path = tmp_path / "missing.log"
    monkeypatch.setattr(http_app, "_template_audit_path", missing_path, raising=False)
    assert http_app._load_template_audit() == []

    class DummyLogRepo:
        def list_recent(self, limit):
            return [
                LogEntry(job_id="job-x", event="failed", level=LogLevel.ERROR, message="boom"),
            ]

    monkeypatch.setattr(http_app, "get_container", lambda: SimpleNamespace(log_repository=DummyLogRepo()))
    incidents = http_app._get_recent_incidents(limit=5)
    assert incidents[0]["job_id"] == "job-x"
    assert incidents[0]["icon"]

    def _raising_container():
        raise RuntimeError("boom")

    monkeypatch.setattr(http_app, "get_container", _raising_container)
    assert http_app._get_recent_incidents(limit=5) == []


def test_get_recent_incidents_handles_missing_repo(monkeypatch):
    monkeypatch.setattr(http_app, "get_container", lambda: SimpleNamespace())
    assert http_app._get_recent_incidents(limit=2) == []


def test_get_recent_incidents_handles_repo_error(monkeypatch):
    class ErrorRepo:
        def list_recent(self, limit):
            raise RuntimeError("boom")

    monkeypatch.setattr(http_app, "get_container", lambda: SimpleNamespace(log_repository=ErrorRepo()))
    assert http_app._get_recent_incidents(limit=2) == []


def test_summarize_session_handles_metadata():
    session = {"session_id": "abcd1234", "metadata": {"display_name": "Ana Silva"}, "created_at": 0}
    summary = http_app._summarize_session(session)
    assert summary["label"] == "Ana Silva"
    assert summary["initials"] == "AN"
    assert http_app._summarize_session(None) is None


def test_get_job_logs_handles_missing_repo(monkeypatch):
    class NoRepo:
        pass

    monkeypatch.setattr(http_app, "get_container", lambda: NoRepo())
    assert http_app._get_job_logs("job-missing") == []


def test_get_job_logs_handles_container_error(monkeypatch):
    def _raise():
        raise RuntimeError("boom")

    monkeypatch.setattr(http_app, "get_container", _raise)
    assert http_app._get_job_logs("job-error") == []


def test_get_job_logs_returns_sorted_entries(monkeypatch):
    now = datetime.now(timezone.utc)
    entries = [
        LogEntry(job_id="job-1", event="start", level=LogLevel.INFO, message="a", timestamp=now),
        LogEntry(job_id="job-1", event="end", level=LogLevel.INFO, message="b", timestamp=now.replace(second=now.second + 1)),
    ]

    class Repo:
        def list_by_job(self, job_id):
            return entries

    monkeypatch.setattr(http_app, "get_container", lambda: SimpleNamespace(log_repository=Repo()))
    logs = http_app._get_job_logs("job-1")
    assert logs[0].event == "end"


def test_normalize_template_id_and_locale(monkeypatch):
    assert http_app._normalize_template_id("Cliente-1") == "cliente-1"
    with pytest.raises(HTTPException):
        http_app._normalize_template_id(" invalid id ")

    assert http_app._normalize_locale_code("pt-BR") == "pt-br"
    assert http_app._normalize_locale_code("") is None
    with pytest.raises(HTTPException):
        http_app._normalize_locale_code("??invalid")


def test_compose_template_file_and_render(tmp_path, monkeypatch):
    content = http_app._compose_template_file("cliente", "Cliente", "desc", "{{header}}", locale="pt-BR")
    assert "locale" in content
    rendered = http_app._render_template_body("{{header}} - {{missing}}", {"header": "Oi"})
    assert rendered == "Oi -"

    audit_path = tmp_path / "templates_audit.log"
    monkeypatch.setattr(http_app, "_template_audit_path", audit_path, raising=False)
    http_app._append_template_audit("create", "cliente", {"name": "Cliente"})
    entries = http_app._load_template_audit(limit=1)
    assert entries[0]["action"] == "create"


def test_available_template_locales_and_guess(monkeypatch):
    class DummyTemplate:
        def __init__(self, locale):
            self.locale = locale

    class DummyRegistry:
        def list_templates(self):
            return [DummyTemplate("pt-br"), DummyTemplate("en-us"), DummyTemplate(None)]

    monkeypatch.setattr(http_app, "_get_template_registry", lambda: DummyRegistry())
    assert http_app._available_template_locales() == ["en-us", "pt-br"]
    assert http_app._guess_locale("pt-BR") == "pt-BR"
    assert http_app._guess_locale("invalid!") is None


def test_serialize_artifacts_handles_enum_and_str():
    artifacts = {
        ArtifactType.TRANSCRIPT_TXT: Path("output/file.txt"),
        "custom": Path("output/custom.json"),
    }
    serialized = http_app._serialize_artifacts_dict(artifacts)
    assert serialized["txt"].endswith("file.txt")
    assert serialized["custom"].endswith("custom.json")
