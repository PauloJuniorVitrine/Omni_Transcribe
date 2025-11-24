from __future__ import annotations

from pathlib import Path

from application.services.artifact_builder import FilesystemArtifactBuilder
from application.services.subtitle_formatter import SubtitleFormatter
from application.services.validator_service import TranscriptValidator
from domain.entities.job import Job
from domain.entities.profile import Profile
from domain.entities.transcription import PostEditResult, Segment
from domain.entities.value_objects import EngineType, JobStatus


class StubTemplateRegistry:
    def __init__(self) -> None:
        self.calls = []

    def render(self, template_id, context, language=None):  # noqa: ANN001
        self.calls.append({"template_id": template_id, "context": context, "language": language})
        return f"rendered-{template_id}-{language}"


def _job(tmp_path: Path) -> Job:
    return Job(
        id="j1",
        source_path=tmp_path / "audio.wav",
        profile_id="p",
        status=JobStatus.PENDING,
        engine=EngineType.OPENAI,
        metadata={},
    )


def _profile(disclaimers=None, meta=None):  # noqa: ANN001
    return Profile(id="p", name="Profile", meta=meta or {}, disclaimers=disclaimers or [])


def _post_edit():
    return PostEditResult(
        text="hello world",
        segments=[Segment(id=0, start=0.0, end=1.0, text="hello world")],
        flags=[],
        language="en",
    )


def test_build_txt_without_template_registry_includes_disclaimers(tmp_path):
    builder = FilesystemArtifactBuilder(tmp_path, SubtitleFormatter(), TranscriptValidator())
    job = _job(tmp_path)
    profile = _profile(disclaimers=["d1", "d2"])
    text = builder._build_txt(job, profile, _post_edit())  # type: ignore[attr-defined]
    assert "Arquivo original: audio.wav" in text
    assert "Perfil editorial: p" in text
    assert "Idioma detectado: en" in text
    assert "- d1" in text and "- d2" in text
    assert "hello world" in text


def test_build_txt_with_template_registry_uses_language_and_template(tmp_path):
    registry = StubTemplateRegistry()
    builder = FilesystemArtifactBuilder(tmp_path, SubtitleFormatter(), TranscriptValidator(), template_registry=registry)
    job = _job(tmp_path)
    job.metadata["delivery_template"] = "custom"
    job.metadata["delivery_locale"] = "fr-fr"
    profile = _profile(meta={"language": "pt-BR"})

    rendered = builder._build_txt(job, profile, _post_edit())  # type: ignore[attr-defined]

    assert rendered == "rendered-custom-fr-fr"
    assert registry.calls, "registry.render should be called"
    call = registry.calls[0]
    assert call["template_id"] == "custom"
    assert call["language"] == "fr-fr"
    assert call["context"]["language"] == "fr-fr"
