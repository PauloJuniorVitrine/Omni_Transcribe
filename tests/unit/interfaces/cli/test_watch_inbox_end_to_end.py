from __future__ import annotations

from pathlib import Path

from interfaces.cli.watch_inbox import InboxEventHandler
from domain.entities.value_objects import EngineType
from domain.usecases.create_job import CreateJobInput


class _SpyContainer:
    def __init__(self, base_input_dir: Path, max_mb: int) -> None:
        self.settings = type("S", (), {"base_input_dir": base_input_dir, "max_audio_size_mb": max_mb, "asr_engine": "openai"})
        self.create_job_use_case = self
        self.pipeline_use_case = None
        self.inputs: list[CreateJobInput] = []

    def execute(self, data: CreateJobInput):
        self.inputs.append(data)
        return type("Job", (), {"id": "job-1"})


def test_watcher_skips_large_and_processes_small(tmp_path):
    container = _SpyContainer(tmp_path, max_mb=1)
    handler = InboxEventHandler(container)
    large = tmp_path / "big.wav"
    large.write_bytes(b"x" * (2 * 1024 * 1024))
    small = tmp_path / "clip.wav"
    small.write_bytes(b"x" * 10)

    handler._handle_audio(large)
    handler._handle_audio(small)

    assert len(container.inputs) == 1
    input_data = container.inputs[0]
    assert input_data.source_path == small
    assert input_data.engine == EngineType.OPENAI
    assert input_data.metadata.get("detected_profile", "") in {"", "geral"}
