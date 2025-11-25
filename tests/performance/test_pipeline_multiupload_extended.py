from __future__ import annotations

import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from domain.entities.value_objects import EngineType
from domain.usecases.create_job import CreateJobInput
from tests.performance.test_pipeline_performance import build_pipeline
from tests.support import stubs


def test_pipeline_sustains_concurrent_uploads(tmp_path: Path) -> None:
    create_job, pipeline, _job_repo = build_pipeline(tmp_path)

    def worker(index: int) -> float:
        audio_path = tmp_path / f"audio-{index}.wav"
        audio_path.write_bytes(b"\x00\x01")
        job = create_job.execute(
            CreateJobInput(source_path=audio_path, engine=EngineType.OPENAI)
        )
        start = time.perf_counter()
        pipeline.execute(job.id)
        return time.perf_counter() - start

    with ThreadPoolExecutor(max_workers=6) as pool:
        durations = list(pool.map(worker, range(12)))

    durations.sort()
    p95 = statistics.quantiles(durations, n=20)[-1]
    assert p95 < 0.7, f"p95 {p95:.4f}s excedeu 0.7s com uploads simultaneos"


def test_pipeline_detects_asr_failure_and_requeues(tmp_path: Path) -> None:
    create_job, pipeline, job_repo = build_pipeline(tmp_path)
    class FlakyAsr(stubs.StubAsrService):
        def __init__(self) -> None:
            super().__init__("persistente")
            self.calls = 0

        def run(self, job, profile, task="transcribe"):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("simulated upstream failure")
            return super().run(job, profile, task=task)

    pipeline.asr_use_case.asr_service = FlakyAsr()
    pipeline.allow_retry = True
    audio_path = tmp_path / "audio.wav"
    audio_path.write_bytes(b"\x01")
    job = create_job.execute(CreateJobInput(source_path=audio_path, engine=EngineType.OPENAI))
    with pytest.raises(RuntimeError):
        pipeline.execute(job.id)

    pending = job_repo.find_by_id(job.id)
    assert pending and pending.status.value == "pending"

    pipeline.execute(job.id)
    final_job = job_repo.find_by_id(job.id)
    assert final_job and final_job.status.value == "awaiting_review"
