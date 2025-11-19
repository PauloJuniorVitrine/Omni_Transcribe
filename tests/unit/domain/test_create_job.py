from __future__ import annotations

from pathlib import Path

from domain.entities.job import Job
from domain.entities.profile import Profile
from domain.entities.value_objects import EngineType, JobStatus, LogLevel
from domain.usecases.create_job import CreateJobFromInbox, CreateJobInput


class InMemoryJobRepository:
    def __init__(self) -> None:
        self.jobs: dict[str, Job] = {}

    def create(self, job: Job) -> Job:
        self.jobs[job.id] = job
        return job

    def update(self, job: Job) -> Job:  # pragma: no cover - not used here
        self.jobs[job.id] = job
        return job

    def find_by_id(self, job_id: str) -> Job | None:  # pragma: no cover
        return self.jobs.get(job_id)

    def list_recent(self, limit: int = 50):  # pragma: no cover
        return list(self.jobs.values())[:limit]


class DummyProfileProvider:
    def __init__(self) -> None:
        self.profile = Profile(
            id="geral",
            meta={"delivery_template": "default", "default_locale": "pt-BR"},
            prompt_body="hello",
        )
        self.requested: list[str] = []

    def get(self, profile_id: str) -> Profile:
        self.requested.append(profile_id)
        if profile_id != self.profile.id:
            raise ValueError("Perfil inexistente")
        return self.profile


class InMemoryLogRepository:
    def __init__(self) -> None:
        self.entries: list[tuple[str, LogLevel]] = []

    def append(self, entry) -> None:  # type: ignore[override]
        self.entries.append((entry.event, entry.level))

    def list_by_job(self, job_id: str):  # pragma: no cover
        return []

    def list_recent(self, limit: int = 20):  # pragma: no cover
        return []


def test_create_job_uses_profile_and_logs_creation(tmp_path: Path) -> None:
    job_repo = InMemoryJobRepository()
    log_repo = InMemoryLogRepository()
    profile_provider = DummyProfileProvider()
    use_case = CreateJobFromInbox(job_repo, profile_provider, log_repo)

    audio_path = tmp_path / "medico" / "consulta.wav"
    audio_path.parent.mkdir()
    audio_path.write_bytes(b"fake")

    result = use_case.execute(
        CreateJobInput(
            source_path=audio_path,
            engine=EngineType.OPENAI,
            metadata={"source": "watcher"},
        )
    )

    assert result.profile_id == "geral"
    assert result.status == JobStatus.PENDING
    assert result.metadata["source_folder"] == "medico"
    assert result.metadata["delivery_template"] == "default"
    assert "delivery_template_updated_at" in result.metadata
    assert result.metadata["delivery_locale"] == "pt-br"
    assert "delivery_locale_updated_at" in result.metadata
    assert job_repo.jobs[result.id] == result
    assert profile_provider.requested == ["geral"]
    assert log_repo.entries == [("job_created", LogLevel.INFO)]


def test_create_job_notifies_status_publisher(tmp_path: Path) -> None:
    job_repo = InMemoryJobRepository()
    log_repo = InMemoryLogRepository()
    profile_provider = DummyProfileProvider()
    status_publisher = StubStatusPublisher()
    use_case = CreateJobFromInbox(job_repo, profile_provider, log_repo, status_publisher=status_publisher)

    audio_path = tmp_path / "geral" / "audio.wav"
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    audio_path.write_bytes(b"x")

    result = use_case.execute(CreateJobInput(source_path=audio_path))

    assert status_publisher.published and status_publisher.published[0].id == result.id
class StubStatusPublisher:
    def __init__(self) -> None:
        self.published: list[Job] = []

    def publish(self, job: Job) -> None:
        self.published.append(job)
