from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from application.services.ports import AsrEngineClient


class FasterWhisperClient(AsrEngineClient):
    """Thin wrapper around faster-whisper for local inference."""

    def __init__(self, model_size: str = "medium", device: str = "cpu") -> None:
        try:
            from faster_whisper import WhisperModel  # type: ignore
        except ImportError as exc:  # pragma: no cover - dependency provided externally
            raise RuntimeError("faster-whisper precisa estar instalado para usar o engine local.") from exc

        self.model = WhisperModel(model_size, device=device)

    def transcribe(self, *, file_path: Path, language: str | None, task: str) -> Dict[str, Any]:
        segments_iter, info = self.model.transcribe(str(file_path), task=task, language=language)
        text_parts: List[str] = []
        segments_payload: List[Dict[str, Any]] = []
        for idx, segment in enumerate(segments_iter):
            text_parts.append(segment.text.strip())
            segments_payload.append(
                {
                    "id": idx,
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip(),
                    "confidence": getattr(segment, "avg_logprob", None),
                }
            )
        return {
            "text": " ".join(text_parts).strip(),
            "segments": segments_payload,
            "language": info.language,
            "duration": info.duration,
        }
