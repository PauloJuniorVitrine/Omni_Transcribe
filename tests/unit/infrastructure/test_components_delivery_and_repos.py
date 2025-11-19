from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from infrastructure.container import components_delivery, components_storage
from infrastructure.database.log_repository import FileLogRepository
from infrastructure.database.review_repository import FileReviewRepository


def _settings(tmp_path: Path, **overrides):
    defaults = dict(
        csv_log_path=tmp_path / "log.csv",
        google_sheets_enabled=False,
        google_sheets_spreadsheet_id="",
        google_sheets_credentials_path=tmp_path / "creds.json",
        google_sheets_worksheet="Jobs",
        base_rejected_dir=tmp_path / "rejected",
        base_backup_dir=tmp_path / "backup",
        profiles_dir=tmp_path / "profiles",
        s3_enabled=False,
        gotranscript_enabled=False,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_build_logging_and_sheet_returns_services(tmp_path):
    settings = _settings(tmp_path)
    sheet_service, status_publisher, rejected_logger = components_delivery.build_logging_and_sheet(settings)
    assert sheet_service is not None
    assert status_publisher is not None
    assert rejected_logger is not None


def test_sheet_gateway_validation():
    settings = _settings(Path("."), google_sheets_enabled=True, google_sheets_spreadsheet_id="")
    with pytest.raises(RuntimeError):
        components_delivery._build_sheet_gateway(settings)  # type: ignore[attr-defined]


def test_build_delivery_services_handles_clients(tmp_path):
    settings = _settings(tmp_path, s3_enabled=False, gotranscript_enabled=False)
    job_repo, artifact_repo, log_repo, review_repo, profile_provider = components_storage.build_repositories(
        tmp_path, settings
    )
    package_service, register_delivery = components_delivery.build_delivery_services(
        settings, job_repo, artifact_repo, components_delivery.CsvSheetService(tmp_path / "log.csv"), log_repo
    )
    assert package_service is not None
    assert register_delivery is not None


def test_file_log_repository_append_and_list(tmp_path):
    repo = FileLogRepository(tmp_path / "logs.json")
    from domain.entities.log_entry import LogEntry
    from domain.entities.value_objects import LogLevel
    from datetime import datetime, timezone

    entry = LogEntry(job_id="job-x", event="test", level=LogLevel.INFO, message="ok", timestamp=datetime.now(timezone.utc))
    repo.append(entry)
    logs = repo.list_by_job("job-x")
    assert logs[0].event == "test"


def test_file_review_repository_save_and_find(tmp_path):
    repo = FileReviewRepository(tmp_path / "reviews.json")
    from domain.entities.user_review import UserReview
    from domain.entities.value_objects import ReviewDecision
    from datetime import datetime, timezone

    review = UserReview(
        id="rev-1",
        job_id="job-1",
        reviewer="Ana",
        decision=ReviewDecision.APPROVED,
        timestamp=datetime.now(timezone.utc),
    )
    repo.save(review)
    latest = repo.find_latest("job-1")
    assert latest and latest.reviewer == "Ana"
