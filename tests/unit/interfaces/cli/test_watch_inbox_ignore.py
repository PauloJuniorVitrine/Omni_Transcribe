from __future__ import annotations

from pathlib import Path

from interfaces.cli.watch_inbox import InboxEventHandler
from infrastructure.container import get_container


class _Container:
    def __init__(self, tmp_path: Path):
        self.settings = type("S", (), {"base_input_dir": tmp_path, "max_audio_size_mb": 1})()
        self.pipeline_use_case = None
        self.create_job_use_case = type("C", (), {"execute": lambda self, input_data: input_data})()


def test_watch_inbox_ignores_invalid_extension(tmp_path: Path, monkeypatch) -> None:
    handler = InboxEventHandler(_Container(tmp_path))
    event = type("E", (), {"is_directory": False, "src_path": str(tmp_path / "file.txt")})()
    handler.on_created(event)
    # no exception means ignored successfully
