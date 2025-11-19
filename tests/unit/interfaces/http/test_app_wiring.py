from __future__ import annotations

import types

import interfaces.http.app as http_app


def test_get_job_controller_dep_uses_container(monkeypatch):
    container = types.SimpleNamespace(
        job_repository=object(),
        create_job_use_case=object(),
        pipeline_use_case=object(),
        retry_use_case=object(),
    )
    monkeypatch.setattr(http_app, "get_container", lambda: container)

    controller = http_app.get_job_controller_dep()

    assert controller.job_repository is container.job_repository
    assert controller.pipeline_use_case is container.pipeline_use_case


def test_get_review_controller_dep_injects_dependencies(monkeypatch):
    container = types.SimpleNamespace(
        job_repository=object(),
        handle_review_use_case=object(),
        sheet_service=object(),
        register_delivery_use_case=object(),
    )
    monkeypatch.setattr(http_app, "get_container", lambda: container)

    controller = http_app.get_review_controller_dep()

    assert controller.job_repository is container.job_repository
    assert controller.sheet_service is container.sheet_service


def test_get_job_log_service_returns_service(monkeypatch):
    class DummyLogRepo:
        def __init__(self):
            self.called = False

        def list_by_job(self, job_id):
            self.called = True
            return []

    repo = DummyLogRepo()
    container = types.SimpleNamespace(log_repository=repo)
    monkeypatch.setattr(http_app, "get_container", lambda: container)

    service = http_app.get_job_log_service()

    service.fetch_all("job-1")
    assert repo.called
