from __future__ import annotations

from pathlib import Path

from application.services.sheet_service import CsvSheetService
from domain.entities.job import Job
from domain.entities.value_objects import EngineType, JobStatus


class StubSheetGateway:
    def __init__(self) -> None:
        self.rows = []

    def append_row(self, row):
        self.rows.append(row)


def make_job(tmp_path: Path) -> Job:
    file_path = tmp_path / "audio.wav"
    file_path.write_text("audio", encoding="utf-8")
    return Job(
        id="job-sheet",
        source_path=file_path,
        profile_id="geral",
        status=JobStatus.APPROVED,
        engine=EngineType.OPENAI,
        duration_sec=120.0,
        language="pt",
        version=2,
    )


def test_csv_sheet_service_logs_and_mirrors(tmp_path: Path):
    gateway = StubSheetGateway()
    csv_path = tmp_path / "logs.csv"
    service = CsvSheetService(csv_path, sheet_gateway=gateway)
    job = make_job(tmp_path)

    artifact_path = tmp_path / "job-sheet" / "files" / "job-sheet_v2.txt"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text("conteudo", encoding="utf-8")

    service.register(job, artifact_path)

    assert csv_path.exists()
    content = csv_path.read_text(encoding="utf-8")
    assert "job-sheet" in content
    assert gateway.rows and gateway.rows[-1]["job_id"] == "job-sheet"
