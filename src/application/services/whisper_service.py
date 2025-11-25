from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional

from domain.entities.job import Job
from domain.entities.profile import Profile
from domain.entities.transcription import Segment, TranscriptionResult
from domain.entities.value_objects import EngineType
from domain.ports.services import AsrService

from .audio_chunker import AudioChunker
from .ports import AsrEngineClient
from .retry import RetryConfig, RetryExecutor


class WhisperService(AsrService):
    """Concrete AsrService that orchestrates OpenAI or local faster-whisper clients."""

    def __init__(
        self,
        engine_clients: Dict[str, AsrEngineClient],
        retry_executor: RetryExecutor[Dict] | None = None,
        default_language: str = "auto",
        chunker: Optional[AudioChunker] = None,
        chunk_trigger_mb: int = 200,
        response_format: str = "verbose_json",
        chunking_strategy: Optional[str] = None,
    ) -> None:
        self.engine_clients = engine_clients
        self.retry_executor = retry_executor or RetryExecutor(RetryConfig())
        self.default_language = default_language
        self.chunker = chunker
        self.chunk_trigger_bytes = chunk_trigger_mb * 1024 * 1024
        self.response_format = response_format
        self.chunking_strategy = chunking_strategy

    def run(self, job: Job, profile: Profile, task: str = "transcribe") -> TranscriptionResult:
        engine_key = job.engine.value
        client = self.engine_clients.get(engine_key)
        if not client:
            raise ValueError(f"Nenhum cliente configurado para o engine {engine_key}")

        language_hint = profile.meta.get("language") if profile.meta else None
        language = None if language_hint in (None, "", "auto") else str(language_hint)
        file_path = Path(job.source_path)

        if job.engine == EngineType.OPENAI and self.chunker and self._should_chunk(file_path):
            return self._run_chunked(job, profile, task, language, client)

        return self._run_single(file_path, language, task, engine_key, client)

    def _run_single(
        self,
        file_path: Path,
        language: Optional[str],
        task: str,
        engine_key: str,
        client: AsrEngineClient,
    ) -> TranscriptionResult:
        def _call() -> Dict:
            return client.transcribe(
                file_path=file_path,
                language=language,
                task=task,
                response_format=self.response_format,
                chunking_strategy=self.chunking_strategy,
            )

        raw = self.retry_executor.run(_call)
        result = self._build_result(raw, engine_key, language, task)
        result.metadata["chunk_count"] = 1
        return result

    def _run_chunked(
        self,
        job: Job,
        profile: Profile,
        task: str,
        language: Optional[str],
        client: AsrEngineClient,
    ) -> TranscriptionResult:
        assert self.chunker
        chunks = self.chunker.split(job.source_path)
        aggregated_segments: List[Segment] = []
        texts: List[str] = []
        language_detected = language or self.default_language
        duration = 0.0
        try:
            for chunk in chunks:
                raw = self.retry_executor.run(
                    lambda p=chunk.path: client.transcribe(
                        file_path=p,
                        language=language,
                        task=task,
                        response_format=self.response_format,
                        chunking_strategy=self.chunking_strategy,
                    )
                )
                chunk_result = self._build_result(raw, job.engine.value, language, task)
                texts.append(chunk_result.text)
                duration = max(duration, chunk.start_sec + (chunk_result.duration_sec or 0))

                for segment in chunk_result.segments:
                    adjusted = Segment(
                        id=segment.id,
                        start=segment.start + chunk.start_sec,
                        end=segment.end + chunk.start_sec,
                        text=segment.text,
                        speaker=segment.speaker,
                        confidence=segment.confidence,
                    )
                    aggregated_segments.append(adjusted)
                language_detected = chunk_result.language or language_detected
        finally:
            for chunk in chunks:
                try:
                    os.remove(chunk.path)
                except OSError:
                    pass

        return TranscriptionResult(
            text=" ".join(texts).strip(),
            segments=aggregated_segments,
            language=language_detected,
            duration_sec=duration,
            engine=job.engine.value,
            metadata={
                "engine": job.engine.value,
                "task": task,
                "chunked": True,
                "chunk_count": len(chunks),
            },
        )

    def _should_chunk(self, file_path: Path) -> bool:
        if not self.chunk_trigger_bytes:
            return False
        try:
            return file_path.stat().st_size > self.chunk_trigger_bytes
        except OSError:
            return False

    def _build_result(self, raw: Dict, engine_key: str, language: Optional[str], task: str) -> TranscriptionResult:
        segments = self._map_segments(raw.get("segments", []))
        text = raw.get("text", "")
        language_detected = raw.get("language") or language or self.default_language
        duration = raw.get("duration") or raw.get("duration_sec")
        metadata = {"engine": engine_key, "task": task, "chunk_count": 0}
        return TranscriptionResult(
            text=text,
            segments=segments,
            language=language_detected,
            duration_sec=duration,
            engine=engine_key,
            metadata=metadata,
        )

    @staticmethod
    def _map_segments(raw_segments: List[Dict]) -> List[Segment]:
        normalized: List[Segment] = []
        for idx, segment in enumerate(raw_segments):
            normalized.append(
                Segment(
                    id=segment.get("id", idx),
                    start=float(segment.get("start", 0.0)),
                    end=float(segment.get("end", 0.0)),
                    text=segment.get("text", "").strip(),
                    speaker=segment.get("speaker"),
                    confidence=segment.get("confidence"),
                )
            )
        return normalized
