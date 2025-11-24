from __future__ import annotations

from datetime import datetime, timezone

from application.services.job_log_service import JobLogQueryResult, JobLogService
from domain.entities.log_entry import LogEntry
from domain.entities.value_objects import LogLevel


class _Repo:
    def __init__(self, entries):
        self.entries = entries

    def list_by_job(self, job_id: str):
        return [e for e in self.entries if e.job_id == job_id]


def _entry(job_id: str, event: str, level: LogLevel = LogLevel.INFO) -> LogEntry:
    return LogEntry(job_id=job_id, event=event, level=level, message=event, timestamp=datetime.now(timezone.utc))


def test_query_filters_and_paginates() -> None:
    entries = [
        _entry("j", "load", LogLevel.INFO),
        _entry("j", "error happened", LogLevel.ERROR),
        _entry("j", "info-two", LogLevel.INFO),
    ]
    service = JobLogService(_Repo(entries))

    result = service.query("j", level="error", event_contains="error", page=1, page_size=1, include_all=False)

    assert isinstance(result, JobLogQueryResult)
    assert result.total == 1
    assert result.logs[0].event == "error happened"
    assert result.has_more is False


def test_query_include_all_ignores_invalid_level() -> None:
    entries = [_entry("j", "first"), _entry("j", "second")]
    service = JobLogService(_Repo(entries))

    result = service.query("j", level="invalid", event_contains="", page=1, page_size=10, include_all=True)

    assert result.total == 2
    assert result.page_size == 2
    assert result.logs[0].timestamp >= result.logs[1].timestamp or result.logs[0].timestamp <= result.logs[1].timestamp


def test_filter_excludes_when_fragment_missing() -> None:
    entries = [_entry("j", "hello", LogLevel.INFO), _entry("j", "other", LogLevel.INFO)]
    service = JobLogService(_Repo(entries))

    result = service.query("j", level="", event_contains="zzz", page=1, page_size=10, include_all=False)

    assert result.total == 0
    assert result.logs == []
