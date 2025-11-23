from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from config import get_settings
from domain.entities.value_objects import EngineType
from domain.usecases.create_job import CreateJobInput
from application.services.audio_chunker import AudioChunker
from infrastructure.container import ServiceContainer, get_container

SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg"}


class InboxEventHandler(FileSystemEventHandler):
    def __init__(self, container: ServiceContainer) -> None:
        super().__init__()
        self.container = container
        self.logger = logging.getLogger("transcribeflow.watch")

    def on_created(self, event) -> None:  # type: ignore[override]
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            return
        self._handle_audio(path)

    def _handle_audio(self, path: Path) -> None:
        base_input = self.container.settings.base_input_dir.resolve()
        max_bytes = self.container.settings.max_audio_size_mb * 1024 * 1024
        if path.stat().st_size > max_bytes:
            self.logger.warning(
                "Arquivo excede limite configurado",
                extra={"event": "file_skipped", "path": str(path), "bytes": path.stat().st_size},
            )
            return
        try:
            relative = path.relative_to(base_input)
            subfolder = relative.parent.name
        except ValueError:
            subfolder = "geral"

        chunk_threshold_mb = getattr(
            self.container.settings, "openai_chunk_trigger_mb", None
        )
        chunk_duration_sec = getattr(
            self.container.settings, "openai_chunk_duration_sec", 900
        )
        if chunk_threshold_mb:
            chunk_bytes = chunk_threshold_mb * 1024 * 1024
            size = path.stat().st_size
            if size > chunk_bytes:
                try:
                    chunker = AudioChunker(chunk_duration_sec=chunk_duration_sec)
                    chunks = chunker.split(path)
                except Exception as exc:
                    self.logger.warning(
                        "Chunking indisponivel; arquivo sera processado integralmente",
                        extra={"path": str(path), "error": str(exc)},
                    )
                    chunks = [None]
                if chunks and chunks[0] is not None:
                    total = len(chunks)
                    for idx, chunk in enumerate(chunks):
                        input_data = CreateJobInput(
                            source_path=chunk.path,
                            profile_id=subfolder if subfolder else "geral",
                            engine=EngineType(self.container.settings.asr_engine),
                            metadata={
                                "detected_profile": subfolder,
                                "chunk_index": idx,
                                "total_chunks": total,
                                "start_sec": chunk.start_sec,
                                "duration_sec": chunk.duration_sec,
                            },
                        )
                        job = self.container.create_job_use_case.execute(input_data)
                        self.logger.info(
                            "Job criado a partir de chunk",
                            extra={"job_id": job.id, "path": str(chunk.path), "chunk": idx},
                        )
                        if self.container.pipeline_use_case:
                            thread = threading.Thread(
                                target=self._run_pipeline, args=(job.id,), daemon=True
                            )
                            thread.start()
                    return

        input_data = CreateJobInput(
            source_path=path,
            profile_id=subfolder if subfolder else "geral",
            engine=EngineType(self.container.settings.asr_engine),
            metadata={"detected_profile": subfolder},
        )
        job = self.container.create_job_use_case.execute(input_data)
        self.logger.info(
            "Job criado a partir do watcher",
            extra={"job_id": job.id, "path": str(path)},
        )

        if self.container.pipeline_use_case:
            thread = threading.Thread(
                target=self._run_pipeline, args=(job.id,), daemon=True
            )
            thread.start()
        else:
            self.logger.warning(
                "Pipeline nao configurado; job aguardando",
                extra={"job_id": job.id},
            )

    def _run_pipeline(self, job_id: str) -> None:
        try:
            assert self.container.pipeline_use_case
            self.container.pipeline_use_case.execute(job_id)
        except Exception as exc:  # pragma: no cover - runtime feedback
            self.logger.error(
                "Falha ao processar job",
                exc_info=True,
                extra={"job_id": job_id, "error": str(exc)},
            )


def main() -> None:
    settings = get_settings()
    container = get_container()
    observer = Observer()
    handler = InboxEventHandler(container)
    watch_path = str(settings.base_input_dir)
    observer.schedule(handler, watch_path, recursive=True)
    observer.start()
    print(f"[Watcher] Monitorando {watch_path} ... pressione Ctrl+C para sair.")
    try:
        while True:
            time.sleep(settings.watcher_poll_interval)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
