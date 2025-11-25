from __future__ import annotations

from pathlib import Path

from application.services.delivery_template_service import DeliveryTemplateRegistry
from config.settings import Settings
from domain.entities.job import Job
from domain.entities.profile import Profile
from domain.entities.value_objects import EngineType, JobStatus
from infrastructure.container import components_artifacts, components_delivery


def test_build_default_builder(tmp_path):
    settings = Settings()
    settings.base_output_dir = tmp_path / "output"
    registry = DeliveryTemplateRegistry(tmp_path / "templates")
    (tmp_path / "templates").mkdir(exist_ok=True)
    template_path = tmp_path / "templates" / "default.template.txt"
    template_path.write_text("---\nid: default\nname: default\ndescription: default template\n---\nHeader\n{{transcript}}\n", encoding="utf-8")
    job = Job(
        id="job1",
        source_path=tmp_path / "audio.wav",
        profile_id="geral",
        status=JobStatus.AWAITING_REVIEW,
        engine=EngineType.OPENAI,
    )
    profile = Profile(id="geral", meta={"subtitle": {}}, prompt_body="body")
    post_edit = type("Dummy", (), {"text": "texto", "segments": [], "flags": [], "language": "pt-BR"})

    builder = components_artifacts.build_default_builder(settings, registry)
    contents = list(builder.build(job, profile, post_edit()))
    assert contents


def test_build_delivery_services_no_integrations(tmp_path):
    settings = Settings()
    settings.base_processing_dir = tmp_path / "processing"
    settings.base_backup_dir = tmp_path / "backup"
    settings.google_sheets_enabled = False
    settings.s3_enabled = False
    settings.gotranscript_enabled = False
    class DummyRepo:
        def __init__(self, path):
            self.path = path

    job_repo = DummyRepo(tmp_path / "jobs.json")
    artifact_repo = DummyRepo(tmp_path / "artifacts.json")
    sheet_service, status_publisher, _ = components_delivery.build_logging_and_sheet(settings)
    assert sheet_service
    assert status_publisher
    package_service, register_delivery = components_delivery.build_delivery_services(
        settings=settings,
        job_repository=job_repo,
        artifact_repository=artifact_repo,
        sheet_service=sheet_service,
        log_repository=DummyRepo(tmp_path / "logs.json"),
    )
    assert package_service
    assert register_delivery
