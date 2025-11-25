from __future__ import annotations

from typing import Dict

from application.services.audio_chunker import AudioChunker
from application.services.chatgpt_service import ChatGptPostEditingService
from application.services.ports import AsrEngineClient
from application.services.whisper_service import WhisperService
from config import Settings
from domain.ports.services import RejectedJobLogger
from domain.usecases.create_job import CreateJobFromInbox
from domain.usecases.handle_review import HandleReviewDecision
from domain.usecases.post_edit import PostEditTranscript
from domain.usecases.retry_or_reject import RetryOrRejectJob
from domain.usecases.run_asr import RunAsrPipeline
from infrastructure.api.faster_whisper_client import FasterWhisperClient
from infrastructure.api.openai_client import OpenAIChatHttpClient, OpenAIWhisperHttpClient

ALLOWED_LOCAL_WHISPER_MODELS = {"tiny", "base", "small", "medium", "large-v2", "large-v3", "turbo"}


def build_core_usecases(
    settings: Settings,
    job_repository,
    profile_provider,
    log_repository,
    review_repository,
    sheet_service,
    status_publisher,
    rejected_logger: RejectedJobLogger,
):
    engine_clients = _build_asr_clients(settings)
    chunker = AudioChunker(settings.openai_chunk_duration_sec)
    asr_service = WhisperService(
        engine_clients,
        chunker=chunker,
        chunk_trigger_mb=settings.openai_chunk_trigger_mb,
        response_format=getattr(settings, "openai_whisper_response_format", "verbose_json"),
        chunking_strategy=getattr(settings, "openai_whisper_chunking_strategy", "") or None,
    )
    chat_client = _build_chat_client(settings)
    post_edit_service = ChatGptPostEditingService(chat_client)

    create_job = CreateJobFromInbox(
        job_repository=job_repository,
        profile_provider=profile_provider,
        log_repository=log_repository,
        status_publisher=status_publisher,
    )
    run_asr = RunAsrPipeline(
        job_repository=job_repository,
        profile_provider=profile_provider,
        asr_service=asr_service,
        log_repository=log_repository,
        status_publisher=status_publisher,
    )
    post_edit = PostEditTranscript(
        job_repository=job_repository,
        profile_provider=profile_provider,
        post_edit_service=post_edit_service,
        log_repository=log_repository,
        status_publisher=status_publisher,
    )
    retry = RetryOrRejectJob(
        job_repository=job_repository,
        log_repository=log_repository,
        rejected_logger=rejected_logger,
        status_publisher=status_publisher,
    )
    handle_review = HandleReviewDecision(
        job_repository=job_repository,
        review_repository=review_repository,
        log_repository=log_repository,
        status_publisher=status_publisher,
    )
    return create_job, run_asr, post_edit, retry, handle_review, asr_service, post_edit_service


def _build_asr_clients(settings: Settings) -> Dict[str, AsrEngineClient]:
    clients: Dict[str, AsrEngineClient] = {}
    whisper_api_key = settings.openai_whisper_api_key or settings.openai_api_key
    if whisper_api_key:
        clients["openai"] = OpenAIWhisperHttpClient(
            api_key=whisper_api_key,
            base_url=settings.openai_base_url,
            model=settings.openai_whisper_model,
        )

    if settings.asr_engine == "local":
        model_size = settings.local_whisper_model_size
        if model_size not in ALLOWED_LOCAL_WHISPER_MODELS:
            raise RuntimeError(
                f"LOCAL_WHISPER_MODEL_SIZE invalido: {model_size}. Use um de {sorted(ALLOWED_LOCAL_WHISPER_MODELS)}."
            )
        clients["local"] = FasterWhisperClient(model_size)
    elif settings.asr_engine == "openai" and "openai" not in clients:
        raise RuntimeError("OPENAI_API_KEY precisa estar configurada para usar o engine openai.")

    if not clients:
        raise RuntimeError("Nenhum cliente ASR disponivel. Configure OpenAI ou faster-whisper.")
    return clients


def _build_chat_client(settings: Settings) -> OpenAIChatHttpClient:
    chat_api_key = settings.chatgpt_api_key or settings.openai_api_key
    if not chat_api_key:
        raise RuntimeError("CHATGPT_API_KEY ou OPENAI_API_KEY obrigatoria para pos-edicao com GPT.")
    return OpenAIChatHttpClient(
        api_key=chat_api_key,
        base_url=settings.openai_base_url,
        model=settings.chatgpt_model or settings.post_edit_model,
    )
