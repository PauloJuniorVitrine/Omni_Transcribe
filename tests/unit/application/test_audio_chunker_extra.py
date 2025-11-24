from __future__ import annotations

import os
import wave
from pathlib import Path
from typing import List

import pytest

from application.services.audio_chunker import AudioChunk, AudioChunker


def _write_silence_wav(path: Path, seconds: int = 2, sample_rate: int = 8000) -> None:
    """Create a simple mono wav file filled with silence."""
    frames = b"\x00\x00" * sample_rate * seconds
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(frames)


def test_split_raises_for_missing_file_without_pydub(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("application.services.audio_chunker.AudioSegment", None)
    missing = tmp_path / "audio.wav"
    chunker = AudioChunker()
    with pytest.raises(RuntimeError):
        chunker.split(missing)


def test_split_wav_multiple_chunks_without_pydub(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("application.services.audio_chunker.AudioSegment", None)
    wav = tmp_path / "long.wav"
    _write_silence_wav(wav, seconds=4, sample_rate=4000)  # 4 seconds
    chunker = AudioChunker(chunk_duration_sec=1)

    chunks = chunker.split(wav)

    assert len(chunks) == 4
    assert all(chunk.path.exists() for chunk in chunks)
    assert {round(chunk.duration_sec, 2) for chunk in chunks} == {1.0}

    # ensure cleanup responsibility stays with caller
    for chunk in chunks:
        os.remove(chunk.path)


def test_split_non_wav_without_pydub_raises(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("application.services.audio_chunker.AudioSegment", None)
    mp3_path = tmp_path / "audio.mp3"
    mp3_path.write_bytes(b"fake")
    chunker = AudioChunker()
    with pytest.raises(RuntimeError):
        chunker.split(mp3_path)


def test_split_with_fake_pydub_uses_export(monkeypatch, tmp_path: Path) -> None:
    class _FakeSegment:
        def __init__(self, duration_ms: int) -> None:
            self._duration_ms = duration_ms
            self.exported: List[Path] = []

        def __len__(self) -> int:
            return self._duration_ms

        def __getitem__(self, item) -> "_FakeSegment":
            start, end = item.start, item.stop
            return _FakeSegment(end - start)

        def export(self, path: Path, format: str) -> None:  # noqa: A003
            path.write_bytes(b"data")
            self.exported.append(path)

    class _FakeAudio:
        def __init__(self) -> None:
            self.segment = _FakeSegment(1500)

        def __len__(self) -> int:
            return len(self.segment)

        def __getitem__(self, item):
            return self.segment.__getitem__(item)

    class _FakeAudioSegment:
        @staticmethod
        def from_file(_path: Path) -> _FakeAudio:
            return _FakeAudio()

    monkeypatch.setattr("application.services.audio_chunker.AudioSegment", _FakeAudioSegment)
    src = tmp_path / "audio.wav"
    src.write_bytes(b"audio")
    chunker = AudioChunker(chunk_duration_sec=1)

    chunks = chunker.split(src)

    assert len(chunks) == 2
    assert all(isinstance(chunk, AudioChunk) for chunk in chunks)
    assert {round(chunk.duration_sec, 2) for chunk in chunks} == {0.5, 1.0}
