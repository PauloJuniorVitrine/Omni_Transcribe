import pytest
from pathlib import Path
from datetime import datetime, timezone

from domain.entities.artifact import Artifact
from domain.entities.delivery_record import DeliveryRecord
from domain.entities.job import Job
from domain.entities.log_entry import LogEntry
from domain.entities.profile import Profile
from domain.entities.transcription import PostEditResult, TranscriptionResult
from domain.entities.value_objects import ArtifactType, EngineType, JobStatus, LogLevel
from domain.usecases.generate_artifacts import GenerateArtifacts
from domain.usecases.handle_review import HandleReviewDecision, ReviewInput
from domain.usecases.retry_or_reject import RetryDecision, RetryOrRejectJob
from domain.usecases.run_asr import RunAsrPipeline
from domain.usecases.post_edit import PostEditTranscript
from domain.usecases.register_delivery import RegisterDelivery


class _DummyRepo:
    def __init__(self, obj=None):
        self.obj = obj
        self.created = []
        self.updated = []
        self.saved = []
        self.logs = []

    def find_by_id(self, _id):
        return self.obj

    def create(self, job):
        self.created.append(job)
        return job

    def update(self, job):
        self.updated.append(job)
        self.obj = job
        return job

    def append(self, entry: LogEntry):
        self.logs.append(entry)

    def save(self, review):
        self.saved.append(review)
        return review

    def save_many(self, artifacts):
        self.saved.extend(artifacts)

    def list_by_job(self, job_id):
        return []


class _FakeProfileProvider:
    def __init__(self, profile: Profile):
        self.profile = profile

    def get(self, _id):
        return self.profile


def _job(status=JobStatus.PENDING, profile_id="p1"):
    return Job(
        id="job1",
        source_path=Path("a.wav"),
        profile_id=profile_id,
        status=status,
        engine=EngineType.OPENAI,
        metadata={},
    )


def test_generate_artifacts_missing_job_raises():
    use_case = GenerateArtifacts(
        job_repository=_DummyRepo(obj=None),
        artifact_repository=_DummyRepo(),
        artifact_builder=lambda *args, **kwargs: [],
        log_repository=_DummyRepo(),
        profile_provider=_FakeProfileProvider(Profile(id="p1", prompt_body="", meta={})),
    )
    with pytest.raises(ValueError):
        use_case.execute("missing", PostEditResult(text="t", segments=[]))


def test_handle_review_missing_job_raises():
    use_case = HandleReviewDecision(
        job_repository=_DummyRepo(obj=None),
        review_repository=_DummyRepo(),
        log_repository=_DummyRepo(),
    )
    with pytest.raises(ValueError):
        use_case.execute(ReviewInput(job_id="missing", reviewer="r", approved=True))


def test_retry_or_reject_rejected_logger_called():
    job = _job()
    repo = _DummyRepo(obj=job)
    rejected = []

    class _RejectedLogger:
        def record(self, job, msg, stage, payload):
            rejected.append((job.id, msg, stage, payload))

    use_case = RetryOrRejectJob(
        job_repository=repo,
        log_repository=_DummyRepo(),
        rejected_logger=_RejectedLogger(),
    )
    decision = RetryDecision(job_id=job.id, error_message="fatal", retryable=False, stage="asr", payload={"x": 1})
    result = use_case.execute(decision)
    assert result.status == JobStatus.REJECTED
    assert rejected == [(job.id, "fatal", "asr", {"x": 1})]


def test_run_asr_failure_sets_failed_and_propagates():
    job = _job()
    repo = _DummyRepo(obj=job)
    log_repo = _DummyRepo()

    class _Asr:
        def run(self, *_args, **_kwargs):
            raise RuntimeError("boom")

    use_case = RunAsrPipeline(
        job_repository=repo,
        profile_provider=_FakeProfileProvider(Profile(id="p1", prompt_body="", meta={})),
        asr_service=_Asr(),
        log_repository=log_repo,
    )
    with pytest.raises(RuntimeError):
        use_case.execute(job.id)
    assert repo.updated[-1].status == JobStatus.FAILED
    assert any(entry.event == "asr_failed" for entry in log_repo.logs)


def test_post_edit_failure_sets_failed_and_propagates():
    job = _job()
    repo = _DummyRepo(obj=job)
    log_repo = _DummyRepo()

    class _Svc:
        def run(self, *_args, **_kwargs):
            raise RuntimeError("oops")

    use_case = PostEditTranscript(
        job_repository=repo,
        profile_provider=_FakeProfileProvider(Profile(id="p1", prompt_body="", meta={})),
        post_edit_service=_Svc(),
        log_repository=log_repo,
    )
    with pytest.raises(RuntimeError):
        use_case.execute(job.id, TranscriptionResult(text="t", segments=[], language="en", duration_sec=1.0))
    assert repo.updated[-1].status == JobStatus.FAILED
    assert any(entry.event == "post_edit_failed" for entry in log_repo.logs)


def test_register_delivery_with_external_client_logs_submission(tmp_path):
    job = _job(status=JobStatus.APPROVED)
    artifacts = [
        Artifact(id="a1", job_id=job.id, path=tmp_path / "a.txt", artifact_type=ArtifactType.TRANSCRIPT_TXT),
    ]
    art_repo = _DummyRepo()
    art_repo.list_by_job = lambda _jid: artifacts  # type: ignore
    log_repo = _DummyRepo()

    class _DeliveryClient:
        def submit_package(self, job, package_path):
            return DeliveryRecord(job_id=job.id, integration="ext", status="ok", external_id="rec1")

    class _PackageSvc:
        def create_package(self, *_args, **_kwargs):
            return tmp_path / "pkg.zip"

    class _DeliveryLogger:
        def register(self, *_args, **_kwargs):
            pass

    use_case = RegisterDelivery(
        job_repository=_DummyRepo(obj=job),
        artifact_repository=art_repo,
        package_service=_PackageSvc(),
        delivery_logger=_DeliveryLogger(),
        log_repository=log_repo,
        delivery_client=_DeliveryClient(),
    )
    path = use_case.execute(job.id)
    assert path.name == "pkg.zip"
    assert any(entry.event == "delivery_external_submitted" for entry in log_repo.logs)


def test_register_delivery_without_artifacts_raises(tmp_path):
    job = _job(status=JobStatus.APPROVED)
    art_repo = _DummyRepo()
    art_repo.list_by_job = lambda _jid: []  # type: ignore
    use_case = RegisterDelivery(
        job_repository=_DummyRepo(obj=job),
        artifact_repository=art_repo,
        package_service=None,  # type: ignore
        delivery_logger=None,  # type: ignore
        log_repository=_DummyRepo(),
    )
    with pytest.raises(ValueError):
        use_case.execute(job.id)
