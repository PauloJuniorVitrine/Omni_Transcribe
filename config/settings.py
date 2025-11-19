from __future__ import annotations

from pathlib import Path
from typing import List, Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global application settings loaded from environment variables."""

    app_env: str = Field(default="development", alias="APP_ENV")

    # Engines and models
    asr_engine: Literal["openai", "local"] = Field(default="openai", alias="ASR_ENGINE")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_whisper_api_key: str = ""
    openai_base_url: str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")
    openai_whisper_model: str = "gpt-4o-mini-transcribe"
    chatgpt_api_key: str = ""
    post_edit_model: str = Field(default="gpt-4.1", alias="POST_EDIT_MODEL")
    chatgpt_model: str = "gpt-4.1"
    local_whisper_model_size: str = Field(default="medium", alias="LOCAL_WHISPER_MODEL_SIZE")

    # Directories
    base_input_dir: Path = Field(default=Path("inbox"), alias="BASE_INPUT_DIR")
    base_output_dir: Path = Field(default=Path("output"), alias="BASE_OUTPUT_DIR")
    base_processing_dir: Path = Field(default=Path("processing"), alias="BASE_PROCESSING_DIR")
    base_backup_dir: Path = Field(default=Path("backup"), alias="BASE_BACKUP_DIR")
    base_rejected_dir: Path = Field(default=Path("rejected"), alias="BASE_REJECTED_DIR")

    # Persistence
    database_url: str = Field(default="sqlite:///transcribeflow.db", alias="DATABASE_URL")
    csv_log_path: Path = Field(default=Path("output/log.csv"), alias="CSV_LOG_PATH")

    # Integrations toggles
    google_sheets_enabled: bool = Field(default=False, alias="GOOGLE_SHEETS_ENABLED")
    google_sheets_credentials_path: Path = Field(
        default=Path("config/credentials.json"), alias="GOOGLE_SHEETS_CREDENTIALS_PATH"
    )
    google_sheets_spreadsheet_id: str = Field(default="", alias="GOOGLE_SHEETS_SPREADSHEET_ID")
    google_sheets_worksheet: str = Field(default="Jobs", alias="GOOGLE_SHEETS_WORKSHEET")
    s3_enabled: bool = Field(default=False, alias="S3_ENABLED")
    s3_bucket: str = Field(default="transcribeflow", alias="S3_BUCKET")
    s3_prefix: str = Field(default="", alias="S3_PREFIX")
    s3_endpoint_url: str = Field(default="", alias="S3_ENDPOINT_URL")
    s3_access_key: str = Field(default="", alias="S3_ACCESS_KEY")
    s3_secret_key: str = Field(default="", alias="S3_SECRET_KEY")
    s3_region: str = Field(default="", alias="S3_REGION")
    gotranscript_enabled: bool = Field(default=False, alias="GOTRANSCRIPT_ENABLED")
    gotranscript_base_url: str = Field(default="https://api.gotranscript.com", alias="GOTRANSCRIPT_BASE_URL")
    gotranscript_api_key: str = Field(default="", alias="GOTRANSCRIPT_API_KEY")
    gotranscript_timeout_sec: int = Field(default=30, alias="GOTRANSCRIPT_TIMEOUT_SEC")

    # Telemetry
    alert_webhook_url: str = Field(default="", alias="ALERT_WEBHOOK_URL")
    metrics_webhook_url: str = Field(default="", alias="METRICS_WEBHOOK_URL")

    # Watcher
    watcher_poll_interval: int = Field(default=5, alias="WATCHER_POLL_INTERVAL")
    max_audio_size_mb: int = Field(default=8192, alias="MAX_AUDIO_SIZE_MB")
    max_request_body_mb: int = Field(default=200, alias="MAX_REQUEST_BODY_MB")
    openai_chunk_trigger_mb: int = Field(default=200, alias="OPENAI_CHUNK_TRIGGER_MB")
    openai_chunk_duration_sec: int = Field(default=900, alias="OPENAI_CHUNK_DURATION_SEC")
    allowed_download_extensions: List[str] = Field(
        default_factory=lambda: ["txt", "srt", "vtt", "json", "zip"], alias="ALLOWED_DOWNLOAD_EXTENSIONS"
    )

    # OAuth / Authentication
    oauth_client_id: str = Field(default="", alias="OAUTH_CLIENT_ID")
    oauth_client_secret: str = Field(default="", alias="OAUTH_CLIENT_SECRET")
    oauth_authorize_url: str = Field(default="", alias="OAUTH_AUTHORIZE_URL")
    oauth_token_url: str = Field(default="", alias="OAUTH_TOKEN_URL")
    oauth_redirect_uri: str = Field(default="", alias="OAUTH_REDIRECT_URI")

    # Webhooks
    webhook_secret: str = Field(default="changeme", alias="WEBHOOK_SECRET")
    webhook_integrations_path: Path = Field(
        default=Path("config/webhook_integrations.json"), alias="WEBHOOK_INTEGRATIONS_PATH"
    )
    webhook_signature_tolerance_sec: int = Field(default=300, alias="WEBHOOK_SIGNATURE_TOLERANCE_SEC")
    session_ttl_minutes: int = Field(default=720, alias="SESSION_TTL_MINUTES")
    accuracy_threshold: float = Field(default=0.99, alias="ACCURACY_THRESHOLD")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def profiles_dir(self) -> Path:
        return Path("profiles")

    def ensure_runtime_directories(self) -> None:
        """
        Guarantee that all base directories exist before processing starts.
        This method is idempotent and safe to call multiple times.
        """
        for directory in [
            self.base_input_dir,
            self.base_output_dir,
            self.base_processing_dir,
            self.base_backup_dir,
            self.base_rejected_dir,
            self.csv_log_path.parent,
        ]:
            Path(directory).mkdir(parents=True, exist_ok=True)
