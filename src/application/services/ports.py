from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Protocol


class AsrEngineClient(Protocol):
    """Generic interface for ASR engines (OpenAI or local faster-whisper)."""

    def transcribe(self, *, file_path: Path, language: str | None, task: str) -> Dict[str, Any]: ...


class ChatModelClient(Protocol):
    """Interface for ChatGPT-like structured completion."""

    def complete(self, *, system_prompt: str, user_prompt: str, response_format: str = "json_object") -> str: ...


class SheetGateway(Protocol):
    """Abstracts persistence of rows into CSV or Google Sheets."""

    def append_row(self, row: Dict[str, Any]) -> None: ...
