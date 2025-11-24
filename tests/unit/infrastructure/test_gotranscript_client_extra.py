from __future__ import annotations

from pathlib import Path

import pytest

from infrastructure.api.gotranscript_client import GoTranscriptClient, _extract_external_id
from domain.entities.job import Job
from domain.entities.value_objects import EngineType, JobStatus
from domain.entities.artifact import Artifact
from domain.entities.value_objects import ArtifactType


def _job(tmp_path: Path) -> Job:
    return Job(
        id="job1",
        source_path=tmp_path / "a.wav",
        profile_id="p",
        status=JobStatus.PENDING,
        engine=EngineType.OPENAI,
        metadata={},
    )


def test_init_raises_when_api_key_missing():
    with pytest.raises(ValueError):
        GoTranscriptClient(base_url="http://x", api_key="")


def test_extract_external_id_returns_none():
    assert _extract_external_id({}) is None
