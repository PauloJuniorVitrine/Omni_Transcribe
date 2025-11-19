from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, Protocol

from ..entities.artifact import Artifact
from ..entities.delivery_record import DeliveryRecord
from ..entities.job import Job
from ..entities.profile import Profile
from ..entities.transcription import PostEditResult, TranscriptionResult


class AsrService(Protocol):
    """Abstracts an ASR engine (OpenAI or local)."""

    def run(self, job: Job, profile: Profile, task: str = "transcribe") -> TranscriptionResult: ...


class PostEditingService(Protocol):
    """Handles post-editing via GPT-like models."""

    def run(self, job: Job, profile: Profile, transcription: TranscriptionResult) -> PostEditResult: ...


class ArtifactBuilder(Protocol):
    """Builds physical artifacts (TXT/SRT/VTT/JSON)."""

    def build(self, job: Job, profile: Profile, post_edit_result: PostEditResult) -> Iterable[Artifact]: ...


class PackageService(Protocol):
    """Creates delivery-ready packages such as ZIP bundles."""

    def create_package(self, job: Job, artifacts: Iterable[Artifact]) -> Path: ...


class DeliveryLogger(Protocol):
    """Registers delivery metadata (CSV/Sheets)."""

    def register(self, job: Job, package_path: Path) -> None: ...


class StorageClient(Protocol):
    """Uploads artifacts to external storage (e.g., S3)."""

    def upload(self, local_path: Path, remote_key: str) -> str: ...


class RejectedJobLogger(Protocol):
    """Persists information about rejected jobs."""

    def record(self, job: Job, error: str, stage: str, payload: Dict[str, object] | None = None) -> Path: ...


class JobStatusPublisher(Protocol):
    """Publishes job status updates."""

    def publish(self, job: Job) -> None: ...


class DeliveryClient(Protocol):
    """Integrates with external delivery endpoints (GoTranscript/clients)."""

    def submit_package(self, job: Job, package_path: Path) -> DeliveryRecord: ...
