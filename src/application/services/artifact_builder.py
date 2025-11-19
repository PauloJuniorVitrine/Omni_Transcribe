from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List
from uuid import uuid4

from domain.entities.artifact import Artifact
from domain.entities.job import Job
from domain.entities.profile import Profile
from domain.entities.transcription import PostEditResult
from domain.entities.value_objects import ArtifactType
from domain.ports.services import ArtifactBuilder

from .subtitle_formatter import SubtitleFormatter
from .validator_service import TranscriptValidator
from .delivery_template_service import DeliveryTemplateRegistry


class FilesystemArtifactBuilder(ArtifactBuilder):
    """Writes TXT/SRT/VTT/JSON artifacts to the output/ directory."""

    def __init__(
        self,
        output_dir: Path,
        subtitle_formatter: SubtitleFormatter,
        validator: TranscriptValidator,
        template_registry: DeliveryTemplateRegistry | None = None,
    ) -> None:
        self.output_dir = output_dir
        self.subtitle_formatter = subtitle_formatter
        self.validator = validator
        self.template_registry = template_registry

    def build(self, job: Job, profile: Profile, post_edit_result: PostEditResult) -> Iterable[Artifact]:
        job_dir = self.output_dir / job.id
        job_dir.mkdir(parents=True, exist_ok=True)
        version_tag = f"v{job.version}"

        artifacts: List[Artifact] = []

        text_path = job_dir / f"{job.id}_{version_tag}.txt"
        text_path.write_text(self._build_txt(job, profile, post_edit_result), encoding="utf-8")
        artifacts.append(self._artifact(job, ArtifactType.TRANSCRIPT_TXT, text_path, job.version))

        srt_content = self.subtitle_formatter.to_srt(post_edit_result.segments, profile)
        srt_path = job_dir / f"{job.id}_{version_tag}.srt"
        srt_path.write_text(srt_content, encoding="utf-8")
        artifacts.append(self._artifact(job, ArtifactType.SUBTITLE_SRT, srt_path, job.version))

        vtt_content = self.subtitle_formatter.to_vtt(post_edit_result.segments, profile)
        vtt_path = job_dir / f"{job.id}_{version_tag}.vtt"
        vtt_path.write_text(vtt_content, encoding="utf-8")
        artifacts.append(self._artifact(job, ArtifactType.SUBTITLE_VTT, vtt_path, job.version))

        warnings = self.validator.validate(profile, post_edit_result.segments)
        json_payload = {
            "job_id": job.id,
            "profile": profile.id,
            "language": post_edit_result.language or job.language,
            "text": post_edit_result.text,
            "segments": [
                {
                    "id": segment.id,
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text,
                    "speaker": segment.speaker,
                }
                for segment in post_edit_result.segments
            ],
            "flags": post_edit_result.flags,
            "warnings": warnings,
            "metadata": job.metadata,
        }
        json_path = job_dir / f"{job.id}_{version_tag}.json"
        json_path.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        artifacts.append(self._artifact(job, ArtifactType.STRUCTURED_JSON, json_path, job.version))

        return artifacts

    def _build_txt(self, job: Job, profile: Profile, post_edit_result: PostEditResult) -> str:
        header_lines = [
            f"Arquivo original: {job.source_path.name}",
            f"Perfil editorial: {profile.id}",
            f"Idioma detectado: {post_edit_result.language or job.language or 'auto'}",
        ]
        disclaimers = profile.disclaimers or profile.meta.get("disclaimers", [])
        if disclaimers:
            header_lines.append("Disclaimers:")
            header_lines.extend([f"- {text}" for text in disclaimers])
        header = "\n".join(header_lines)
        body = post_edit_result.text.strip()
        if not self.template_registry:
            return f"{header}\n\n{body}\n"

        template_id = job.metadata.get("delivery_template") or profile.meta.get("delivery_template")
        language = job.metadata.get("delivery_locale") or post_edit_result.language or job.language or profile.meta.get("language")
        rendered = self.template_registry.render(
            template_id,
            {
                "header": header,
                "transcript": body,
                "job_id": job.id,
                "profile_id": profile.id,
                "language": language or "auto",
            },
            language=language,
        )
        return rendered

    @staticmethod
    def _artifact(job: Job, artifact_type: ArtifactType, path: Path, version: int) -> Artifact:
        return Artifact(
            id=uuid4().hex,
            job_id=job.id,
            artifact_type=artifact_type,
            path=path,
            version=version,
        )
