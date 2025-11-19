from __future__ import annotations

from pathlib import Path

import pytest

from application.controllers.review_controller import ReviewController
from application.services.sheet_service import CsvSheetService
from domain.entities.job import Job
from domain.entities.value_objects import EngineType, JobStatus
from domain.usecases.handle_review import ReviewInput


class DummyJobRepo:
    def __init__(self):
        self.jobs = {
            "job-1": Job(
                id="job-1",
                source_path=Path("inbox/audio.wav"),
                profile_id="geral",
                engine=EngineType.OPENAI,
                status=JobStatus.AWAITING_REVIEW,
            )
        }

    def find_by_id(self, job_id: str):
        return self.jobs.get(job_id)


class DummyHandleReview:
    def __init__(self):
        self.inputs = []

    def execute(self, payload: ReviewInput):
        self.inputs.append(payload)


class DummyRegisterDelivery:
    def __init__(self):
        self.calls = []

    def execute(self, job_id: str):
        self.calls.append(job_id)


def test_submit_review_without_delivery(tmp_path):
    repo = DummyJobRepo()
    handler = DummyHandleReview()
    sheet = CsvSheetService(tmp_path / "log.csv")
    controller = ReviewController(repo, handler, sheet_service=sheet)

    job = controller.submit_review("job-1", reviewer="Ana", approved=False, notes="needs fix")
    assert job.id == "job-1"
    assert handler.inputs[-1].approved is False


def test_submit_review_triggers_delivery(tmp_path):
    repo = DummyJobRepo()
    handler = DummyHandleReview()
    delivery = DummyRegisterDelivery()
    sheet = CsvSheetService(tmp_path / "log.csv")
    controller = ReviewController(repo, handler, sheet_service=sheet, register_delivery_use_case=delivery)

    controller.submit_review("job-1", reviewer="Ana", approved=True, notes=None)
    assert delivery.calls == ["job-1"]


def test_submit_review_missing_job_throws(tmp_path):
    repo = DummyJobRepo()
    handler = DummyHandleReview()
    sheet = CsvSheetService(tmp_path / "log.csv")
    controller = ReviewController(repo, handler, sheet)

    with pytest.raises(ValueError):
        controller.submit_review("missing", reviewer="Ana", approved=True, notes=None)
