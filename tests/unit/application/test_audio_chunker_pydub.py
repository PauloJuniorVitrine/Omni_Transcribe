from __future__ import annotations

from pathlib import Path

import pytest

from application.services.audio_chunker import AudioChunker


class _FakeAudio:
    def __init__(self):
        self._exported = []

    def __len__(self):
        return 1500  # ms

    def __getitem__(self, item):
        class _Slice:
            def __len__(self_inner):
                return 500

            def export(self_inner, path, format):
                path.write_bytes(b"data")

        return _Slice()

    def export(self, path, format):
        path.write_bytes(b"data")


def test_split_with_pydub_path(monkeypatch, tmp_path: Path) -> None:
    fake_audio = _FakeAudio()

    class _AudioSegment:
        @staticmethod
        def from_file(_path):
            return fake_audio

    monkeypatch.setattr("application.services.audio_chunker.AudioSegment", _AudioSegment)
    audio = tmp_path / "file.mp3"
    audio.write_bytes(b"x")
    chunker = AudioChunker(chunk_duration_sec=1)

    chunks = chunker.split(audio)

    # Audio de 1500ms com chunk de 1000ms gera 2 partes (500ms cada no fake)
    assert len(chunks) == 2
    assert chunks[0].duration_sec == pytest.approx(0.5, rel=1e-2)
    assert chunks[1].start_sec == pytest.approx(1.0, rel=1e-3)
    assert all(chunk.path.exists() for chunk in chunks)
