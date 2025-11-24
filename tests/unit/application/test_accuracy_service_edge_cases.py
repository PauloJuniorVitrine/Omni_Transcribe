from __future__ import annotations

from pathlib import Path

from application.services.accuracy_service import TranscriptionAccuracyGuard
from domain.entities.job import Job
from domain.entities.log_entry import LogEntry
from domain.entities.transcription import PostEditResult, Segment, TranscriptionResult
from domain.entities.value_objects import EngineType, JobStatus
from tests.support import stubs


def _guard(tmp_path: Path) -> TranscriptionAccuracyGuard:
    job_repo = stubs.MemoryJobRepository()
    log_repo = stubs.MemoryLogRepository()
    return TranscriptionAccuracyGuard(job_repository=job_repo, log_repository=log_repo, threshold=0.9)


def test_resolve_metadata_reference_inline(tmp_path):
    guard = _guard(tmp_path)
    job = Job(
        id="j1",
        source_path=tmp_path / "a.wav",
        profile_id="p",
        status=JobStatus.PENDING,
        engine=EngineType.OPENAI,
        metadata={"reference_transcript": "inline ref"},
    )
    guard.job_repository.create(job)
    assert guard._resolve_metadata_reference(job) == "inline ref"


def test_resolve_metadata_reference_invalid_and_missing_paths(tmp_path):
    guard = _guard(tmp_path)
    job = Job(
        id="j2",
        source_path=tmp_path / "a.wav",
        profile_id="p",
        status=JobStatus.PENDING,
        engine=EngineType.OPENAI,
        metadata={"reference_path": 123},  # invalid type
    )
    assert guard._resolve_metadata_reference(job) is None

    job.metadata["reference_path"] = str(tmp_path / "missing.txt")
    assert guard._resolve_metadata_reference(job) is None

    # Path exists but read_text will raise IsADirectoryError (OSError subclass)
    dir_path = tmp_path / "dirref"
    dir_path.mkdir(parents=True, exist_ok=True)
    job.metadata["reference_path"] = str(dir_path)
    assert guard._resolve_metadata_reference(job) is None


def test_resolve_metadata_reference_reads_file(tmp_path):
    guard = _guard(tmp_path)
    ref = tmp_path / "ref.txt"
    ref.write_text("reference content", encoding="utf-8")
    job = Job(
        id="j3",
        source_path=tmp_path / "a.wav",
        profile_id="p",
        status=JobStatus.PENDING,
        engine=EngineType.OPENAI,
        metadata={"reference_path": str(ref)},
    )
    assert guard._resolve_metadata_reference(job) == "reference content"


def test_word_error_rate_edge_cases(tmp_path):
    guard = _guard(tmp_path)
    # both empty
    assert guard._word_error_rate("", "") == 0.0
    # reference empty, hypothesis non-empty
    assert guard._word_error_rate("", "hyp") == 1.0
    # hypothesis empty, reference non-empty
    assert guard._word_error_rate("ref words", "") == 1.0


def test_estimate_confidence_penalty_empty_segments(tmp_path):
    guard = _guard(tmp_path)
    post = PostEditResult(text="text", segments=[], flags=[], language="en")
    assert guard._estimate_confidence_penalty(post) == 0.0


def test_evaluate_uses_client_reference_when_better(tmp_path):
    job_repo = stubs.MemoryJobRepository()
    log_repo = stubs.MemoryLogRepository()
    ref_text = "hello world"

    guard = TranscriptionAccuracyGuard(
        job_repository=job_repo,
        log_repository=log_repo,
        threshold=0.5,
        reference_loader=lambda job: ref_text,
    )

    job = Job(
        id="job-ref",
        source_path=tmp_path / "a.wav",
        profile_id="p",
        status=JobStatus.PENDING,
        engine=EngineType.OPENAI,
        metadata={},
    )
    job_repo.create(job)

    asr = TranscriptionResult(
        text="hello wurld",
        segments=[Segment(id=0, start=0.0, end=1.0, text="hello wurld")],
        language="en",
        duration_sec=1.0,
        engine="openai",
        metadata={},
    )
    post = PostEditResult(
        text="hello world",
        segments=[Segment(id=0, start=0.0, end=1.0, text="hello world", confidence=0.9)],
        flags=[],
        language="en",
    )

    guard.evaluate(job_id=job.id, transcription=asr, post_edit=post)

    updated = job_repo.find_by_id(job.id)
    assert updated is not None
    assert updated.metadata["accuracy_reference_source"] == "client_reference"
    # WER against reference should be lower than WER against asr output
    assert float(updated.metadata["accuracy_wer"]) < float(updated.metadata["accuracy_wer_asr"])
    # Log was appended
    assert any(isinstance(entry, LogEntry) and entry.event == "accuracy_evaluated" for entry in log_repo.entries)
