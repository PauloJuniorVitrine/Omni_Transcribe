from __future__ import annotations

import wave
from pathlib import Path

import pytest

from application.services.audio_chunker import AudioChunker


def _write_wav(path: Path, seconds: float, frame_rate: int = 8000) -> None:
    """Helper to write a silent WAV with the requested duration."""
    n_frames = int(frame_rate * seconds)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(frame_rate)
        handle.writeframes(b"\x00\x00" * n_frames)


def test_split_wav_fallback_single_chunk(tmp_path: Path, monkeypatch) -> None:
    # Force fallback path (pydub unavailable)
    monkeypatch.setattr("application.services.audio_chunker.AudioSegment", None)
    source = tmp_path / "audio.wav"
    _write_wav(source, seconds=0.5, frame_rate=8000)
    chunker = AudioChunker(chunk_duration_sec=1)

    chunks = chunker.split(source)

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.path.exists()
    assert chunk.start_sec == 0
    assert pytest.approx(chunk.duration_sec, rel=1e-2) == 0.5


def test_split_wav_fallback_multiple_chunks(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("application.services.audio_chunker.AudioSegment", None)
    source = tmp_path / "audio.wav"
    _write_wav(source, seconds=2.0, frame_rate=8000)
    chunker = AudioChunker(chunk_duration_sec=1)

    chunks = chunker.split(source)

    assert len(chunks) == 2
    assert chunks[0].duration_sec == pytest.approx(1.0, rel=1e-2)
    assert chunks[1].start_sec == pytest.approx(chunks[0].duration_sec, rel=1e-3)


def test_split_non_wav_without_pydub_raises(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("application.services.audio_chunker.AudioSegment", None)
    source = tmp_path / "audio.mp3"
    source.write_bytes(b"\x00")
    chunker = AudioChunker(chunk_duration_sec=1)

    with pytest.raises(RuntimeError):
        chunker.split(source)


def test_split_missing_file_without_pydub_raises(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("application.services.audio_chunker.AudioSegment", None)
    source = tmp_path / "missing.wav"
    chunker = AudioChunker(chunk_duration_sec=1)

    with pytest.raises(RuntimeError):
        chunker.split(source)
