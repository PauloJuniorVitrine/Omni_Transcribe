from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List

try:
    from pydub import AudioSegment  # type: ignore
except ImportError:  # pragma: no cover
    AudioSegment = None


@dataclass
class AudioChunk:
    path: Path
    start_sec: float
    duration_sec: float


class AudioChunker:
    """Utility that splits large audio files into smaller chunks."""

    def __init__(self, chunk_duration_sec: int = 900) -> None:
        self.chunk_duration_ms = chunk_duration_sec * 1000

    def split(self, file_path: Path) -> List[AudioChunk]:
        if AudioSegment is None:
            raise RuntimeError("pydub é necessário para executar o chunking de áudio.")
        audio = AudioSegment.from_file(file_path)
        chunks: List[AudioChunk] = []
        for start_ms in range(0, len(audio), self.chunk_duration_ms):
            end_ms = min(start_ms + self.chunk_duration_ms, len(audio))
            segment = audio[start_ms:end_ms]
            fd, tmp_name = tempfile.mkstemp(suffix=file_path.suffix or ".wav")
            os.close(fd)
            tmp_path = Path(tmp_name)
            segment.export(tmp_path, format=file_path.suffix.lstrip(".") or "wav")
            chunks.append(
                AudioChunk(
                    path=tmp_path,
                    start_sec=start_ms / 1000.0,
                    duration_sec=len(segment) / 1000.0,
                )
            )
        return chunks
