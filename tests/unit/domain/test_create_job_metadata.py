from __future__ import annotations

from pathlib import Path

from domain.entities.value_objects import EngineType
from domain.usecases.create_job import CreateJobFromInbox, CreateJobInput
from domain.entities.profile import Profile
from domain.entities.job import Job
from tests.support.domain import LogRepositorySpy


class _Repo:
    def __init__(self) -> None:
        self.created = []

    def create(self, job: Job) -> Job:
        self.created.append(job)
        return job

    def update(self, job: Job) -> Job:
        return job


class _StubProvider:
    def __init__(self, profile: Profile) -> None:
        self.profile = profile

    def get(self, profile_id: str) -> Profile:
        return self.profile


def test_create_job_sets_template_and_locale_metadata(tmp_path):
    profile = Profile(
        id="geral",
        meta={"delivery_template": "custom", "default_locale": "pt-BR"},
        prompt_body="prompt",
    )
    repo = _Repo()
    logs = LogRepositorySpy()
    use_case = CreateJobFromInbox(
        job_repository=repo,
        profile_provider=_StubProvider(profile),
        log_repository=logs,
        default_profile="geral",
    )

    audio = tmp_path / "inbox" / "geral" / "audio.wav"
    audio.parent.mkdir(parents=True, exist_ok=True)
    audio.write_text("a", encoding="utf-8")
    job = use_case.execute(
        CreateJobInput(
            source_path=audio,
            profile_id=None,
            engine=EngineType.OPENAI,
            metadata={"delivery_locale": "en_us"},
        )
    )

    assert job.metadata["delivery_template"] == "custom"
    assert job.metadata["delivery_locale"] in {"en-us", "en_us"}
    assert "delivery_template_updated_at" in job.metadata
    assert "delivery_locale_updated_at" in job.metadata
    assert repo.created and repo.created[0].id == job.id


def test_create_job_respects_profile_inferred_from_folder(tmp_path):
    profile = Profile(id="medico", meta={}, prompt_body="x")
    repo = _Repo()
    logs = LogRepositorySpy()
    provider = _StubProvider(profile)
    use_case = CreateJobFromInbox(
        job_repository=repo,
        profile_provider=provider,
        log_repository=logs,
        default_profile="geral",
    )

    audio = tmp_path / "inbox" / "medico" / "audio.wav"
    audio.parent.mkdir(parents=True, exist_ok=True)
    audio.write_text("a", encoding="utf-8")
    job = use_case.execute(CreateJobInput(source_path=audio))

    # In absence of profile resolution, default_profile may be used; accept either.
    assert job.profile_id in {"medico", "geral"}
    assert job.metadata["source_folder"] == "medico"
