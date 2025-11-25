from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import wave

from interfaces.cli.watch_inbox import InboxEventHandler
from domain.entities.value_objects import EngineType
from domain.usecases.create_job import CreateJobInput
from application.services.audio_chunker import AudioChunker, AudioChunk


class _ChunkingContainer:
    def __init__(self, base_input_dir: Path) -> None:
        self.settings = SimpleNamespace(
            base_input_dir=base_input_dir,
            max_audio_size_mb=10,
            asr_engine="openai",
            openai_chunk_trigger_mb=0.001,
            openai_chunk_duration_sec=1,
        )
        self.create_job_use_case = self
        self.pipeline_use_case = None
        self.inputs: list[CreateJobInput] = []

    def execute(self, data: CreateJobInput):
        self.inputs.append(data)
        return SimpleNamespace(id="job-chunk")


def test_watcher_uses_chunking_threshold(tmp_path, monkeypatch):
    container = _ChunkingContainer(tmp_path)
    handler = InboxEventHandler(container)
    big_file = tmp_path / "clip.wav"
    # write 2s silence wav so fallback chunker can operate without pydub
    with wave.open(str(big_file), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(8000)
        wf.writeframes(b"\x00\x00" * 8000 * 2)

    handler._handle_audio(big_file)

    assert len(container.inputs) >= 1
    assert all(inp.engine == EngineType.OPENAI for inp in container.inputs)


def test_watcher_skips_too_large_file_with_log(tmp_path, caplog):
    container = _ChunkingContainer(tmp_path)
    handler = InboxEventHandler(container)
    caplog.set_level("WARNING", logger="transcribeflow.watch")
    monkeypatch = None  # silence lint

    huge_file = tmp_path / "huge.wav"
    # > max size configured in _ChunkingContainer (10 MB)
    huge_file.write_bytes(b"x" * (12 * 1024 * 1024))

    handler._handle_audio(huge_file)

    assert not container.inputs
