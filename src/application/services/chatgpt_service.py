from __future__ import annotations

import json
from typing import Dict, List

from domain.entities.job import Job
from domain.entities.profile import Profile
from domain.entities.transcription import PostEditResult, Segment, TranscriptionResult
from domain.ports.services import PostEditingService

from .pii import mask_text
from .ports import ChatModelClient
from .retry import RetryConfig, RetryExecutor


class ChatGptPostEditingService(PostEditingService):
    """Concrete implementation of the post-editing stage using ChatGPT."""

    def __init__(self, client: ChatModelClient, retry_executor: RetryExecutor[str] | None = None) -> None:
        self.client = client
        self.retry_executor = retry_executor or RetryExecutor(RetryConfig())

    def run(self, job: Job, profile: Profile, transcription: TranscriptionResult) -> PostEditResult:
        system_prompt = self._build_system_prompt(profile)
        user_prompt = self._build_user_prompt(profile, transcription)

        def _call() -> str:
            return self.client.complete(system_prompt=system_prompt, user_prompt=user_prompt, response_format="json_object")

        raw_response = self.retry_executor.run(_call)
        payload = self._safe_parse_payload(raw_response, transcription)

        text = payload.get("text", transcription.text)
        segments_payload = payload.get("segments") or self._segments_from_transcription(transcription)
        flags = payload.get("flags", [])

        if profile.should_anonymize_pii():
            text = mask_text(text)
            segments_payload = [{**segment, "text": mask_text(segment.get("text", ""))} for segment in segments_payload]

        segments = [self._map_segment(idx, segment) for idx, segment in enumerate(segments_payload)]

        return PostEditResult(
            text=text,
            segments=segments,
            flags=flags,
            language=payload.get("language") or transcription.language,
        )

    @staticmethod
    def _build_system_prompt(profile: Profile) -> str:
        disclaimers = "\n".join(profile.disclaimers or profile.meta.get("disclaimers", []))
        return (
            "Voce e um editor especializado em transcricoes profissionais.\n"
            "Aplique o modo clean verbatim, normalize pontuacao e siga o perfil abaixo.\n"
            f"Disclaimers obrigatorios:\n{disclaimers}\n"
        )

    @staticmethod
    def _build_user_prompt(profile: Profile, transcription: TranscriptionResult) -> str:
        instructions = profile.meta.get("instructions", [])
        payload: Dict[str, object] = {
            "profile_meta": profile.meta,
            "instructions": instructions,
            "transcription": {
                "text": transcription.text,
                "language": transcription.language,
                "segments": [
                    {
                        "id": segment.id,
                        "start": segment.start,
                        "end": segment.end,
                        "text": segment.text,
                        "speaker": segment.speaker,
                    }
                    for segment in transcription.segments
                ],
            },
        }
        return json.dumps(payload, ensure_ascii=False)

    @staticmethod
    def _segments_from_transcription(transcription: TranscriptionResult) -> List[Dict[str, object]]:
        return [
            {"id": segment.id, "start": segment.start, "end": segment.end, "text": segment.text, "speaker": segment.speaker}
            for segment in transcription.segments
        ]

    @staticmethod
    def _map_segment(idx: int, segment: Dict[str, object]) -> Segment:
        return Segment(
            id=int(segment.get("id", idx)),
            start=float(segment.get("start", 0.0)),
            end=float(segment.get("end", 0.0)),
            text=str(segment.get("text", "")),
            speaker=segment.get("speaker"),
        )

    @staticmethod
    def _safe_parse_payload(raw_response: str, transcription: TranscriptionResult) -> Dict[str, object]:
        """
        Robustez: garante payload minimamente valido; em caso de erro, retorna fallback baseado na transcricao.
        """
        try:
            payload = json.loads(raw_response or "") or {}
        except Exception:
            return {"text": transcription.text, "segments": ChatGptPostEditingService._segments_from_transcription(transcription), "flags": []}

        # sane defaults
        if not isinstance(payload, dict):
            return {"text": transcription.text, "segments": ChatGptPostEditingService._segments_from_transcription(transcription), "flags": []}

        text = payload.get("text") if isinstance(payload.get("text"), str) else transcription.text
        segments = payload.get("segments")
        if not isinstance(segments, list):
            segments = ChatGptPostEditingService._segments_from_transcription(transcription)
        flags = payload.get("flags") if isinstance(payload.get("flags"), list) else []

        return {"text": text, "segments": segments, "flags": flags, "language": payload.get("language")}
