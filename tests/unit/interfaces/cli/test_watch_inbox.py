from __future__ import annotations

import logging
from pathlib import Path
from types import SimpleNamespace
import os

os.environ.setdefault("CREDENTIALS_SECRET_KEY", "eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHg=")

import pytest

from interfaces.cli.watch_inbox import InboxEventHandler, main


class DummyUseCase:
    def __init__(self) -> None:
        self.inputs: list = []

    def execute(self, data):
        self.inputs.append(data)
        return SimpleNamespace(id="job-123")


def _build_container(
    base_dir: Path,
    *,
    asr_engine: str = "openai",
    pipeline=None,
    max_mb: int = 2,
    input_dir: Path | None = None,
):
    settings = SimpleNamespace(
        base_input_dir=input_dir or base_dir,
        max_audio_size_mb=max_mb,
        asr_engine=asr_engine,
        watcher_poll_interval=1,
    )
    container = SimpleNamespace(
        settings=settings,
        create_job_use_case=DummyUseCase(),
        pipeline_use_case=pipeline,
    )
    return container


def test_handle_audio_skips_large_file(tmp_path):
    container = _build_container(tmp_path, max_mb=0)
    handler = InboxEventHandler(container)
    file_path = tmp_path / "audio.wav"
    file_path.write_bytes(b"x" * 10)

    handler._handle_audio(file_path)

    assert container.create_job_use_case.inputs == []


def test_handle_audio_creates_job_and_runs_pipeline(tmp_path, monkeypatch):
    executed: list[str] = []

    class Pipeline:
        def execute(self, job_id: str) -> None:
            executed.append(job_id)

    container = _build_container(tmp_path, pipeline=Pipeline())
    handler = InboxEventHandler(container)
    audio_dir = tmp_path / "geral"
    audio_dir.mkdir()
    file_path = audio_dir / "clip.wav"
    file_path.write_bytes(b"x")

    thread_calls: dict = {}

    def fake_thread(target, args, daemon):
        thread_calls["target"] = target
        thread_calls["args"] = args

        class _Thread:
            def start(self_inner):
                target(*args)

        return _Thread()

    monkeypatch.setattr("interfaces.cli.watch_inbox.threading.Thread", fake_thread)

    handler._handle_audio(file_path)

    assert container.create_job_use_case.inputs
    assert executed == ["job-123"]
    assert thread_calls["args"] == ("job-123",)


def test_run_pipeline_logs_error(tmp_path, monkeypatch):
    class BrokenPipeline:
        def execute(self, job_id: str) -> None:
            raise RuntimeError("boom")

    container = _build_container(tmp_path, pipeline=BrokenPipeline())
    handler = InboxEventHandler(container)
    captured: list[tuple] = []

    class DummyLogger:
        def error(self, message, *args, **kwargs):
            captured.append((message, args, kwargs))

    handler.logger = DummyLogger()

    handler._run_pipeline("job-x")

    assert captured and "Falha ao processar job" in captured[0][0]


def test_on_created_ignores_directories(tmp_path, monkeypatch):
    container = _build_container(tmp_path)
    handler = InboxEventHandler(container)
    calls: list[Path] = []
    handler._handle_audio = lambda path: calls.append(path)  # type: ignore[assignment]

    handler.on_created(SimpleNamespace(is_directory=True, src_path=str(tmp_path / "audio.wav")))

    assert calls == []


def test_on_created_ignores_unsupported_extension(tmp_path):
    container = _build_container(tmp_path)
    handler = InboxEventHandler(container)
    calls: list[Path] = []
    handler._handle_audio = lambda path: calls.append(path)  # type: ignore[assignment]

    handler.on_created(SimpleNamespace(is_directory=False, src_path=str(tmp_path / "notes.txt")))

    assert calls == []


def test_handle_audio_defaults_profile_when_outside_input(tmp_path):
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    container = _build_container(tmp_path, input_dir=input_dir)
    handler = InboxEventHandler(container)
    external_file = tmp_path / "external.wav"
    external_file.write_bytes(b"x")

    handler._handle_audio(external_file)

    assert container.create_job_use_case.inputs[0].profile_id == "geral"
    assert container.create_job_use_case.inputs[0].metadata["detected_profile"] == "geral"


def test_on_created_triggers_handle_audio(tmp_path):
    container = _build_container(tmp_path)
    handler = InboxEventHandler(container)
    recorded = []
    handler._handle_audio = lambda path: recorded.append(path)  # type: ignore[assignment]

    handler.on_created(SimpleNamespace(is_directory=False, src_path=str(tmp_path / "audio.wav")))

    assert recorded == [tmp_path / "audio.wav"]


def test_main_handles_keyboard_interrupt(monkeypatch, tmp_path):
    events: dict[str, object] = {}

    class DummySettings:
        base_input_dir = tmp_path
        watcher_poll_interval = 0.1

    monkeypatch.setattr("interfaces.cli.watch_inbox.get_settings", lambda: DummySettings())
    container = SimpleNamespace()
    monkeypatch.setattr("interfaces.cli.watch_inbox.get_container", lambda: container)

    class DummyObserver:
        def __init__(self):
            events["initialized"] = True

        def schedule(self, handler, path, recursive):
            events["scheduled"] = (handler, path, recursive)

        def start(self):
            events["started"] = True

        def stop(self):
            events["stopped"] = True

        def join(self):
            events["joined"] = True

    monkeypatch.setattr("interfaces.cli.watch_inbox.Observer", lambda: DummyObserver())

    class DummyHandler:
        def __init__(self, received_container):
            events["handler_container"] = received_container

    monkeypatch.setattr("interfaces.cli.watch_inbox.InboxEventHandler", DummyHandler)

    def fake_sleep(_):
        raise KeyboardInterrupt()

    monkeypatch.setattr("interfaces.cli.watch_inbox.time.sleep", fake_sleep)

    main()

    assert events["handler_container"] is container
    assert events.get("stopped") and events.get("joined")


def test_handle_audio_logs_when_pipeline_missing(tmp_path, caplog):
    container = _build_container(tmp_path, pipeline=None)
    handler = InboxEventHandler(container)
    audio = tmp_path / "one.wav"
    audio.write_bytes(b"x")

    class DummyLogger:
        def __init__(self):
            self.messages: list[str] = []

        def warning(self, message, *args, **kwargs):
            self.messages.append(message)

        def info(self, *args, **kwargs):
            pass

    dummy_logger = DummyLogger()
    handler.logger = dummy_logger  # type: ignore[assignment]

    handler._handle_audio(audio)

    assert dummy_logger.messages and "Pipeline" in dummy_logger.messages[0]
