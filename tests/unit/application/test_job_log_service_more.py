from __future__ import annotations

from datetime import datetime, timezone

from application.services.job_log_service import JobLogService
from domain.entities.log_entry import LogEntry
from domain.entities.value_objects import LogLevel


class _Repo:
    def __init__(self, entries):
        self.entries = entries

    def list_by_job(self, job_id: str):
        return [e for e in self.entries if e.job_id == job_id]


def _log(job_id: str, event: str, level: LogLevel, message=None):
    return LogEntry(job_id=job_id, event=event, level=level, message=message, timestamp=datetime.now(timezone.utc))


def test_job_log_service_include_all_pagesize_and_invalid_level() -> None:
    entries = [_log("j1", "a", LogLevel.INFO), _log("j1", "b", LogLevel.ERROR, message=None)]
    service = JobLogService(_Repo(entries))

    result = service.query("j1", level="invalid", event_contains="", page=1, page_size=1, include_all=True)

    assert result.page_size == 2
    assert result.total == 2
    payload = JobLogService.serialize(result.logs[1])
    assert "timestamp" in payload and payload["level"] in {"info", "error"}
