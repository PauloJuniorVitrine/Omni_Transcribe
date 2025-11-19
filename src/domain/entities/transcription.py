from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Segment:
    """Represents a single transcription segment with timestamps."""

    id: int
    start: float
    end: float
    text: str
    speaker: Optional[str] = None
    confidence: Optional[float] = None


@dataclass
class TranscriptionResult:
    """Raw output from the ASR engine."""

    text: str
    segments: List[Segment]
    language: str
    duration_sec: Optional[float] = None
    engine: str = "openai"
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class PostEditResult:
    """Structured output from the post-editing step."""

    text: str
    segments: List[Segment]
    flags: List[Dict[str, str]] = field(default_factory=list)
    language: Optional[str] = None
