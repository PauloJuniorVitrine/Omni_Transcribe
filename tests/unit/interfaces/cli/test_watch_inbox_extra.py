import types
from pathlib import Path

from interfaces.cli.watch_inbox import InboxEventHandler, SUPPORTED_EXTENSIONS


class _Container:
    def __init__(self, tmp_path: Path):
        self.settings = types.SimpleNamespace(
            base_input_dir=tmp_path,
            max_audio_size_mb=10,
            openai_chunk_trigger_mb=None,
            openai_chunk_duration_sec=900,
            asr_engine="openai",
        )
        self.created_inputs = []

        class _CreateUseCase:
            def __init__(self, outer):
                self.outer = outer

            def execute(self, input_data):
                self.outer.created_inputs.append(input_data)
                return types.SimpleNamespace(id="job1")

        self.create_job_use_case = _CreateUseCase(self)
        self.pipeline_use_case = None


def test_watch_inbox_ignores_unsupported_extension(tmp_path):
    container = _Container(tmp_path)
    handler = InboxEventHandler(container)
    bogus = types.SimpleNamespace(is_directory=False, src_path=str(tmp_path / "file.txt"))
    handler.on_created(bogus)
    assert container.created_inputs == []


def test_watch_inbox_chunking_exception_falls_back_to_full_file(tmp_path, monkeypatch):
    container = _Container(tmp_path)
    path = tmp_path / "audio.wav"
    path.write_bytes(b"x" * (2 * 1024 * 1024))  # 2MB
    container.settings.openai_chunk_trigger_mb = 1

    class _Chunk:
        def __init__(self):
            self.path = path
            self.start_sec = 0
            self.duration_sec = 1.0

    class _Chunker:
        def __init__(self, *_args, **_kwargs):
            pass

        def split(self, _p):
            raise RuntimeError("chunk fail")

    monkeypatch.setattr("interfaces.cli.watch_inbox.AudioChunker", _Chunker)
    handler = InboxEventHandler(container)
    event = types.SimpleNamespace(is_directory=False, src_path=str(path))
    handler.on_created(event)

    # Mesmo apos falha no chunking, deve processar o arquivo inteiro.
    assert container.created_inputs
    assert Path(container.created_inputs[0].source_path) == path
