from __future__ import annotations

import pytest
from datetime import datetime, timezone

from interfaces.http import app as http_app
from domain.entities.job import Job
from domain.entities.value_objects import EngineType, JobStatus


def _make_job(job_id: str, metadata=None):
    return Job(
        id=job_id,
        source_path=http_app.Path(f"inbox/{job_id}.wav"),
        profile_id="geral",
        engine=EngineType.OPENAI,
        status=JobStatus.PENDING,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        metadata=metadata or {},
    )


def test_compute_accuracy_summary_counts_and_average():
    jobs = [
        _make_job("job-1", {"accuracy_score": "0.99", "accuracy_status": "passing", "accuracy_wer": "0.01"}),
        _make_job("job-2", {"accuracy_score": "0.95", "accuracy_status": "needs_review", "accuracy_wer": "0.08"}),
        _make_job("job-3", {}),
    ]
    summary = http_app._compute_accuracy_summary(jobs)
    assert summary["evaluated"] == 2
    assert summary["needs_review"] == 1
    assert summary["passing"] == 1
    assert pytest.approx(summary["average_score"], rel=1e-3) == 0.97
    assert pytest.approx(summary["average_wer"], rel=1e-3) == 0.045


def test_compose_accuracy_snapshot_returns_badge():
    job = _make_job(
        "job-1",
        {
            "accuracy_score": "0.98",
            "accuracy_status": "passing",
            "accuracy_wer": "0.02",
            "accuracy_baseline": "0.98",
            "accuracy_penalty": "0.0",
            "accuracy_updated_at": "2025-11-14T10:00:00Z",
            "accuracy_reference_source": "client_reference",
        },
    )
    snapshot = http_app._compose_accuracy_snapshot(job)
    assert snapshot["badge"] == "success"
    assert snapshot["wer"].endswith("%")
    assert snapshot["reference_source"] == "client_reference"


def test_enforce_download_rate(monkeypatch):
    monkeypatch.setattr(http_app, "_DOWNLOAD_RATE_LIMIT", 2)
    http_app._download_tracker.clear()
    http_app._enforce_download_rate("session-id")
    http_app._enforce_download_rate("session-id")
    with pytest.raises(http_app.HTTPException) as exc:
        http_app._enforce_download_rate("session-id")
    assert exc.value.status_code == 429
