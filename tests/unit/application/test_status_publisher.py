from __future__ import annotations

from domain.entities.job import Job
from domain.entities.value_objects import EngineType
from application.services.status_publisher import SheetStatusPublisher


class StubSheetService:
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.calls: list[str] = []

    def record_job_status(self, job: Job, status: str) -> None:
        if self.should_fail:
            raise RuntimeError("sheets offline")
        self.calls.append(f"{job.id}:{status}")


def test_status_publisher_records_successfully(tmp_path):
    sheet = StubSheetService()
    publisher = SheetStatusPublisher(sheet)
    job = Job(id="job1", source_path=tmp_path / "file.wav", profile_id="geral", engine=EngineType.OPENAI)
    publisher.publish(job)
    assert sheet.calls == ["job1:pending"]


def test_status_publisher_handles_failures_gracefully(tmp_path, caplog):
    sheet = StubSheetService(should_fail=True)
    publisher = SheetStatusPublisher(sheet)
    job = Job(id="job2", source_path=tmp_path / "file.wav", profile_id="geral", engine=EngineType.OPENAI)
    publisher.publish(job)
    assert sheet.calls == []
    assert any("Falha ao registrar job job2" in message for message in caplog.text.splitlines())
