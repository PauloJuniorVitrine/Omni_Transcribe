from __future__ import annotations

from enum import Enum


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    ASR_COMPLETED = "asr_completed"
    POST_EDITING = "post_editing"
    AWAITING_REVIEW = "awaiting_review"
    APPROVED = "approved"
    ADJUSTMENTS_REQUIRED = "adjustments_required"
    FAILED = "failed"
    REJECTED = "rejected"


class ArtifactType(str, Enum):
    TRANSCRIPT_TXT = "txt"
    SUBTITLE_SRT = "srt"
    SUBTITLE_VTT = "vtt"
    STRUCTURED_JSON = "json"
    PACKAGE_ZIP = "zip"


class EngineType(str, Enum):
    OPENAI = "openai"
    LOCAL = "local"


class ReviewDecision(str, Enum):
    APPROVED = "approved"
    NEEDS_ADJUSTMENT = "needs_adjustment"


class LogLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
