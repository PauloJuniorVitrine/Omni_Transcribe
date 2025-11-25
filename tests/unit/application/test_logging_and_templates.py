from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from application.logging_config import JsonLogFormatter, configure_logging
from application.services.delivery_template_service import DeliveryTemplateRegistry
from application.services.audio_chunker import AudioChunker


def test_json_log_formatter_outputs_structured_payload():
    formatter = JsonLogFormatter()
    record = logging.LogRecord(
        name="transcribeflow.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="evento teste",
        args=(),
        exc_info=None,
    )
    formatted = formatter.format(record)
    payload = json.loads(formatted)
    assert payload["message"] == "evento teste"
    assert payload["level"] == "INFO"


def test_configure_logging_is_idempotent(monkeypatch):
    logger = configure_logging("DEBUG")
    assert logger.level == logging.DEBUG
    handler_count = len(logger.handlers)
    second = configure_logging("INFO")
    assert second is logger
    assert len(logger.handlers) == handler_count

def test_configure_logging_ignores_reconfiguration(monkeypatch):
    import application.logging_config as logging_config_module

    root_logger = logging.getLogger()
    initial_handlers = list(root_logger.handlers)
    monkeypatch.setattr(logging_config_module, "_configured", True)

    logger = configure_logging("WARNING")

    assert logger is logging.getLogger("transcribeflow")
    assert len(root_logger.handlers) == len(initial_handlers)
    assert logger.level == logging.WARNING


def test_configure_logging_skips_handler_registration_after_first(tmp_path, monkeypatch):
    root_logger = logging.getLogger()
    handler_count = len(root_logger.handlers)
    # simulate partial config by leaving _configured False but reusing JsonLogFormatter path
    monkeypatch.setattr("application.logging_config._configured", False)
    first = configure_logging("INFO")
    second = configure_logging("DEBUG")
    assert first is second
    assert len(root_logger.handlers) == handler_count + 1


def test_delivery_template_registry_lists_and_render(tmp_path):
    template_path = tmp_path / "default.template.txt"
    template_path.write_text("---\nid: default\nname: Default\nlocale: pt-BR\n---\nOlá {{name}}\n", encoding="utf-8")
    registry = DeliveryTemplateRegistry(tmp_path)
    templates = registry.list_templates()
    assert templates[0].id == "default"
    rendered = registry.render("default", {"name": "Ana"})
    assert "Ana" in rendered


def test_delivery_template_registry_localized(tmp_path):
    (tmp_path / "pt-br").mkdir(parents=True)
    (tmp_path / "pt-br" / "default.template.txt").write_text("---\nlocale: pt-BR\n---\nOi {{name}}\n", encoding="utf-8")
    template_path = tmp_path / "default.template.txt"
    template_path.write_text("---\nid: default\n---\nHello {{name}}\n", encoding="utf-8")
    registry = DeliveryTemplateRegistry(tmp_path)
    rendered = registry.render("default", {"name": "Ana"}, language="pt-BR")
    assert "Oi" in rendered


def test_delivery_template_registry_missing_template(tmp_path):
    registry = DeliveryTemplateRegistry(tmp_path)
    with pytest.raises(FileNotFoundError):
        registry._load_template(tmp_path / "missing.template.txt")


def test_delivery_template_registry_default_fallback(tmp_path):
    template_path = tmp_path / "custom.template.txt"
    template_path.write_text("Hello {{name}}\n", encoding="utf-8")
    registry = DeliveryTemplateRegistry(tmp_path)
    assert registry.default_template_id == "custom"
    rendered = registry.render(None, {"name": "Ana"})
    assert "Ana" in rendered


def test_delivery_template_registry_locale_inference_and_prefix(tmp_path):
    base = tmp_path / "report.template.txt"
    base.write_text("---\nid: report\n---\nReport {{name}}\n", encoding="utf-8")
    localized_dir = tmp_path / "pt"
    localized_dir.mkdir()
    localized = localized_dir / "report.template.txt"
    localized.write_text("{{name}} Relat\u00f3rio\n", encoding="utf-8")
    registry = DeliveryTemplateRegistry(tmp_path)

    pt_render = registry.render("report", {"name": "Ana"}, language="pt-BR")
    assert "Relatório" in pt_render


def test_delivery_template_split_front_matter_without_yaml():
    metadata, body = DeliveryTemplateRegistry._split_front_matter("Sem front matter")
    assert metadata == {}
    assert "Sem front matter" in body


def test_audio_chunker_requires_pydub(monkeypatch):
    chunker = AudioChunker(chunk_duration_sec=5)
    monkeypatch.setattr("application.services.audio_chunker.AudioSegment", None)
    with pytest.raises(RuntimeError):
        chunker.split(Path("fake.wav"))


def test_audio_chunker_splits_using_stub(monkeypatch, tmp_path):
    class DummySegment:
        def __init__(self, length):
            self.length = length

        def __len__(self):
            return self.length

        def __getitem__(self, slice_obj):
            return DummySegment(slice_obj.stop - slice_obj.start)

        def export(self, out_path, format):
            Path(out_path).write_bytes(b"stub")

    class DummyAudioSegment:
        @staticmethod
        def from_file(path):
            return DummySegment(6000)

    monkeypatch.setattr("application.services.audio_chunker.AudioSegment", DummyAudioSegment)
    chunker = AudioChunker(chunk_duration_sec=3)
    chunks = chunker.split(tmp_path / "fake.wav")
    assert len(chunks) == 2
    for chunk in chunks:
        assert chunk.path.exists()
