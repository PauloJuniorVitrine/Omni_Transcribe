from __future__ import annotations

import os
import tempfile
import wave
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
        if AudioSegment is not None:
            return self._split_with_pydub(file_path)
        if not file_path.exists():
            raise RuntimeError("pydub e necessario para chunking de formatos nao-WAV.")
        return self._split_wav_fallback(file_path)

    def _split_with_pydub(self, file_path: Path) -> List[AudioChunk]:
        audio = AudioSegment.from_file(file_path)
        return self._export_chunks(audio, file_path)

    def _split_wav_fallback(self, file_path: Path) -> List[AudioChunk]:
        if file_path.suffix.lower() not in {".wav", ".wave"}:
            raise RuntimeError("pydub e necessario para chunking de formatos nao-WAV.")
        chunks: List[AudioChunk] = []
        with wave.open(str(file_path), "rb") as src:
            params = src.getparams()
            frame_rate = params.framerate
            frames_per_chunk = int(frame_rate * (self.chunk_duration_ms / 1000.0))
            total_frames = src.getnframes()
            start_frame = 0
            while start_frame < total_frames:
                src.setpos(start_frame)
                frames = src.readframes(frames_per_chunk)
                fd, tmp_name = tempfile.mkstemp(suffix=".wav")
                os.close(fd)
                with wave.open(tmp_name, "wb") as dst:
                    dst.setparams(params)
                    dst.writeframes(frames)
                chunk_frames = len(frames) // params.sampwidth // params.nchannels
                chunks.append(
                    AudioChunk(
                        path=Path(tmp_name),
                        start_sec=start_frame / frame_rate,
                        duration_sec=chunk_frames / frame_rate,
                    )
                )
                start_frame += frames_per_chunk
        return chunks

    def _export_chunks(self, audio, file_path: Path) -> List[AudioChunk]:
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
