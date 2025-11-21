from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from domain.entities.job import Job
from domain.entities.log_entry import LogEntry
from domain.entities.transcription import PostEditResult, TranscriptionResult
from domain.entities.value_objects import LogLevel
from domain.ports.repositories import JobRepository, LogRepository


@dataclass
class TranscriptionAccuracyGuard:
    """Evaluates transcription quality and records metadata/logs."""

    job_repository: JobRepository
    log_repository: LogRepository
    threshold: float = 0.99
    reference_loader: Optional[Callable[[Job], Optional[str]]] = None
    metric_dispatcher: Optional[Callable[[str, Dict[str, Any]], None]] = None
    alert_dispatcher: Optional[Callable[[str, Dict[str, Any]], None]] = None

    def evaluate(self, job_id: str, transcription: TranscriptionResult, post_edit: PostEditResult) -> None:
        job = self.job_repository.find_by_id(job_id)
        if not job:
            return
        reference_text = self.reference_loader(job) if self.reference_loader else self._resolve_metadata_reference(job)
        score_payload = self._calculate_score(transcription, post_edit, reference_text)
        score = score_payload["score"]
        job.metadata = job.metadata or {}
        job.metadata.update(
            {
                "accuracy_score": f"{score:.4f}",
                "accuracy_baseline": f"{score_payload['baseline']:.4f}",
                "accuracy_penalty": f"{score_payload['penalty']:.4f}",
                "accuracy_wer": f"{score_payload['wer_active']:.4f}",
                "accuracy_wer_asr": f"{score_payload['wer_asr']:.4f}",
                "accuracy_reference_source": score_payload["reference_source"],
                "accuracy_status": "passing" if score >= self.threshold else "needs_review",
                "accuracy_method": "heuristic_v2",
                "accuracy_requires_review": "true" if score < self.threshold else "false",
                "accuracy_language": post_edit.language or transcription.language or "",
                "accuracy_updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        if score_payload.get("wer_reference") is not None:
            job.metadata["accuracy_wer_reference"] = f"{score_payload['wer_reference']:.4f}"

        self.job_repository.update(job)

        level = LogLevel.INFO if score >= self.threshold else LogLevel.WARNING
        message = (
            f"Acuracia estimada {score:.2%} (WER {score_payload['wer_active']:.2%})."
            if score >= self.threshold
            else f"Acuracia abaixo do alvo ({score:.2%}, WER {score_payload['wer_active']:.2%}). Job marcado para revisao."
        )
        self.log_repository.append(LogEntry(job_id=job_id, event="accuracy_evaluated", level=level, message=message))
        metric_payload = {
            "job_id": job_id,
            "score": score,
            "baseline": score_payload["baseline"],
            "penalty": score_payload["penalty"],
            "wer_active": score_payload["wer_active"],
            "reference_source": score_payload["reference_source"],
            "requires_review": score < self.threshold,
        }
        if self.metric_dispatcher:
            self.metric_dispatcher("accuracy.guard.evaluated", metric_payload)
        if score < self.threshold and self.alert_dispatcher:
            self.alert_dispatcher(
                "accuracy.guard.alert",
                {
                    "job_id": job_id,
                    "score": score,
                    "wer_active": score_payload["wer_active"],
                    "threshold": self.threshold,
                },
            )

    def _calculate_score(
        self,
        transcription: TranscriptionResult,
        post_edit: PostEditResult,
        reference_text: Optional[str] = None,
    ) -> Dict[str, Optional[float] | float | str]:
        wer_asr = self._word_error_rate(post_edit.text, transcription.text)
        reference_source = "asr_output"
        wer_reference: Optional[float] = None
        baseline_wer = wer_asr
        if reference_text:
            wer_reference = self._word_error_rate(post_edit.text, reference_text)
            if wer_reference < wer_asr:
                baseline_wer = wer_reference
                reference_source = "client_reference"
        baseline = max(0.0, 1.0 - baseline_wer)
        penalty = self._estimate_penalty(post_edit)
        score = max(0.0, baseline - penalty)
        return {
            "score": score,
            "baseline": baseline,
            "penalty": penalty,
            "wer_active": baseline_wer,
            "wer_asr": wer_asr,
            "wer_reference": wer_reference,
            "reference_source": reference_source,
        }

    def _estimate_penalty(self, post_edit: PostEditResult) -> float:
        tokens = max(1, len(self._tokenize(post_edit.text)))
        placeholder_penalty = post_edit.text.count("???") / tokens
        flag_penalty = len(post_edit.flags) * 0.02
        wordings_penalty = self._estimate_confidence_penalty(post_edit)
        return min(0.6, placeholder_penalty + flag_penalty + wordings_penalty)

    @staticmethod
    def _estimate_confidence_penalty(post_edit: PostEditResult) -> float:
        low_conf_segments = 0
        for segment in post_edit.segments or []:
            if segment.confidence is not None and segment.confidence < 0.85:
                low_conf_segments += 1
        if not post_edit.segments:
            return 0.0
        return min(0.3, (low_conf_segments / len(post_edit.segments)) * 0.3)

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        normalized = unicodedata.normalize("NFKD", text or "").casefold()
        normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
        cleaned = re.sub(r"[^a-z0-9\s]", " ", normalized)
        return [token for token in cleaned.split() if token]

    def _word_error_rate(self, reference: str, hypothesis: str) -> float:
        reference_tokens = self._tokenize(reference)
        hypothesis_tokens = self._tokenize(hypothesis)
        if not reference_tokens and not hypothesis_tokens:
            return 0.0
        if not reference_tokens:
            return 1.0
        distance = self._levenshtein(reference_tokens, hypothesis_tokens)
        return min(1.0, distance / max(1, len(reference_tokens)))

    @staticmethod
    def _levenshtein(reference: List[str], hypothesis: List[str]) -> int:
        if not reference:
            return len(hypothesis)
        if not hypothesis:
            return len(reference)
        previous = list(range(len(hypothesis) + 1))
        for i, ref_token in enumerate(reference, start=1):
            current = [i]
            for j, hyp_token in enumerate(hypothesis, start=1):
                cost = 0 if ref_token == hyp_token else 1
                insertion = current[-1] + 1
                deletion = previous[j] + 1
                substitution = previous[j - 1] + cost
                current.append(min(insertion, deletion, substitution))
            previous = current
        return previous[-1]

    @staticmethod
    def _resolve_metadata_reference(job: Job) -> Optional[str]:
        metadata = job.metadata or {}
        inline = metadata.get("reference_transcript")
        if inline:
            return inline
        reference_path = metadata.get("reference_path")
        if not reference_path:
            return None
        try:
            path = Path(reference_path)
        except TypeError:
            return None
        if not path.exists():
            return None
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return None


__all__ = ["TranscriptionAccuracyGuard"]
