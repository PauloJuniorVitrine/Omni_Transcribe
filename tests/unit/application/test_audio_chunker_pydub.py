from __future__ import annotations

from pathlib import Path

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

    assert len(chunks) == 3  # 1500ms broken into 3 parts of 500ms
    assert all(chunk.path.exists() for chunk in chunks)
