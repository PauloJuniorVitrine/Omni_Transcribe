from __future__ import annotations

from pathlib import Path

import pytest

from types import ModuleType
import sys

from infrastructure.api.faster_whisper_client import FasterWhisperClient


class DummyModel:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str | None]] = []

    def transcribe(self, file_path: str, task: str, language: str | None):
        self.calls.append((file_path, task, language))

        class Segment:
            def __init__(self, idx: int) -> None:
                self.id = idx
                self.start = idx * 1.0
                self.end = idx * 1.0 + 0.5
                self.text = f"segment {idx}"
                self.avg_logprob = -0.1

        segments = [Segment(0), Segment(1)]

        class Info:
            language = "pt"
            duration = 10.0

        return segments, Info()


def test_faster_whisper_client(monkeypatch, tmp_path: Path):
    dummy_model = DummyModel()

    class DummyLoader:
        def __init__(self, model_size, device):
            self._model = dummy_model

        def transcribe(self, *args, **kwargs):
            return self._model.transcribe(*args, **kwargs)

    fake_module = ModuleType("faster_whisper")
    fake_module.WhisperModel = DummyLoader
    monkeypatch.setitem(sys.modules, "faster_whisper", fake_module)

    client = FasterWhisperClient("medium", device="cpu")
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"\x00\x01")

    result = client.transcribe(file_path=audio, language="pt", task="translate")

    assert dummy_model.calls == [(str(audio), "translate", "pt")]
    assert result["language"] == "pt"
    assert len(result["segments"]) == 2
    assert result["segments"][0]["text"] == "segment 0"
