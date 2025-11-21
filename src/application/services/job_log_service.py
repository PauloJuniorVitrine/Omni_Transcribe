from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from domain.entities.log_entry import LogEntry
from domain.entities.value_objects import LogLevel


@dataclass
class JobLogQueryResult:
    logs: List[LogEntry]
    total: int
    page: int
    page_size: int
    has_more: bool


class JobLogService:
    """Encapsula consulta e paginacao de logs por job."""

    def __init__(self, log_repository) -> None:
        self._log_repository = log_repository

    def fetch_all(self, job_id: str) -> List[LogEntry]:
        entries = self._log_repository.list_by_job(job_id)
        return sorted(entries, key=lambda entry: entry.timestamp, reverse=True)

    def query(
        self,
        job_id: str,
        level: str,
        event_contains: str,
        page: int,
        page_size: int,
        include_all: bool,
    ) -> JobLogQueryResult:
        entries = self.fetch_all(job_id)
        filtered = self._filter(entries, level, event_contains)
        total = len(filtered)
        if include_all:
            return JobLogQueryResult(
                logs=filtered,
                total=total,
                page=1,
                page_size=total if total else page_size,
                has_more=False,
            )
        page = max(page, 1)
        page_size = max(page_size, 1)
        start = (page - 1) * page_size
        subset = filtered[start : start + page_size]
        has_more = start + page_size < total
        return JobLogQueryResult(
            logs=subset,
            total=total,
            page=page,
            page_size=page_size,
            has_more=has_more,
        )

    @staticmethod
    def serialize(entry: LogEntry) -> Dict[str, str]:
        return {
            "job_id": entry.job_id,
            "event": entry.event,
            "message": entry.message,
            "level": entry.level.value,
            "timestamp": entry.timestamp.isoformat(),
        }

    def _filter(self, entries: List[LogEntry], level: str, event_contains: str) -> List[LogEntry]:
        target_level = (level or "").lower()
        event_fragment = (event_contains or "").lower()
        if target_level and target_level not in {item.value for item in LogLevel}:
            target_level = ""
        filtered = []
        for entry in entries:
            if target_level and entry.level.value != target_level:
                continue
            if event_fragment and event_fragment not in entry.event.lower():
                continue
            filtered.append(entry)
        return filtered


__all__ = ["JobLogService", "JobLogQueryResult"]
