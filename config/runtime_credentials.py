from __future__ import annotations

import base64
import json
import os
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

try:
    from cryptography.fernet import Fernet, InvalidToken
except ModuleNotFoundError:  # pragma: no cover - fallback for minimal environments
    class InvalidToken(Exception):
        """Fallback InvalidToken when cryptography is unavailable."""

    class Fernet:  # type: ignore[override]
        """No-op Fernet replacement used only for dev/test scaffolding."""

        def __init__(self, key: bytes) -> None:  # noqa: D401 - simple stub
            self.key = key

        def encrypt(self, data: bytes) -> bytes:
            return data

        def decrypt(self, token: bytes) -> bytes:
            return token
try:
    from filelock import FileLock
except ModuleNotFoundError:  # pragma: no cover - fallback for stub envs
    class FileLock:  # type: ignore[override]
        """Minimal FileLock fallback when dependency is missing."""

        def __init__(self, *_args, **_kwargs) -> None:
            self._locked = False

        def __enter__(self) -> "FileLock":
            self._locked = True
            return self

        def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
            self._locked = False

        def acquire(self, *_args, **_kwargs) -> None:
            self._locked = True

        def release(self) -> None:
            self._locked = False


SECRET_CACHE_FILE = ".credentials_secret.key"


DEFAULT_CREDENTIALS: Dict[str, Dict[str, str]] = {
    "whisper": {"api_key": "", "model": "gpt-4o-mini-transcribe"},
    "chatgpt": {"api_key": "", "model": "gpt-4.1-mini"},
}


@dataclass
class RuntimeCredentialStore:
    path: Path = field(default_factory=lambda: Path("config/runtime_credentials.json"))
    audit_path: Path = field(default_factory=lambda: Path("config/runtime_credentials_audit.log"))
    _secret_path: Path = field(init=False)

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = FileLock(str(self.path) + ".lock")
        self._secret_path = self.path.parent / SECRET_CACHE_FILE
        secret = os.getenv("CREDENTIALS_SECRET_KEY") or os.getenv("RUNTIME_CREDENTIALS_KEY")
        if not secret:
            secret, cached = self._load_or_create_secret()
            self._secret_loaded_from_cache = cached
        else:
            self._secret_loaded_from_cache = False
        self._cipher = self._build_cipher(secret)
        if not self._cipher:
            raise RuntimeError(
                "CREDENTIALS_SECRET_KEY precisa ser definido para usar o cofre de credenciais."
            )
        skip_verify = bool(os.environ.get("SKIP_RUNTIME_CREDENTIALS_VERIFY"))
        if self.path.exists():
            if not skip_verify:
                self.read()
        else:
            self._write(DEFAULT_CREDENTIALS)
            self._append_audit_entry("bootstrap", {})

    def read(self) -> Dict[str, Dict[str, str]]:
        with self.lock:
            if not self.path.exists():
                return json.loads(json.dumps(DEFAULT_CREDENTIALS))
            raw = self.path.read_text(encoding="utf-8").strip()
        if not raw:
            return json.loads(json.dumps(DEFAULT_CREDENTIALS))
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # File corruption  fallback to defaults
            return json.loads(json.dumps(DEFAULT_CREDENTIALS))

        if isinstance(data, dict) and data.get("encrypted"):
            if not self._cipher:
                raise RuntimeError(
                    "Credenciais criptografadas exigem CREDENTIALS_SECRET_KEY definido no ambiente."
                )
            payload = data.get("payload", "")
            try:
                decrypted = self._cipher.decrypt(payload.encode("utf-8"))
            except InvalidToken:
                if not getattr(self, "_secret_loaded_from_cache", False):
                    raise RuntimeError("No foi possvel descriptografar as credenciais.")
                self._reset_credentials()
                return json.loads(json.dumps(DEFAULT_CREDENTIALS))
            return json.loads(decrypted.decode("utf-8"))

        if isinstance(data, dict):
            # Migracao automatica para formato criptografado
            self._write(data)
            return data
        return json.loads(json.dumps(DEFAULT_CREDENTIALS))

    def save(self, payload: Dict[str, Dict[str, str]]) -> Dict[str, Dict[str, str]]:
        data = {
            "whisper": {**DEFAULT_CREDENTIALS["whisper"], **payload.get("whisper", {})},
            "chatgpt": {**DEFAULT_CREDENTIALS["chatgpt"], **payload.get("chatgpt", {})},
        }
        self._write(data)
        self._append_audit_entry("save", self._summarize_changes(data))
        return data

    def update(
        self,
        whisper_api_key: str | None = None,
        whisper_model: str | None = None,
        chatgpt_api_key: str | None = None,
        chatgpt_model: str | None = None,
    ) -> Dict[str, Dict[str, str]]:
        data = self.read()
        if whisper_api_key is not None:
            data["whisper"]["api_key"] = whisper_api_key.strip()
        if whisper_model is not None:
            data["whisper"]["model"] = whisper_model.strip()
        if chatgpt_api_key is not None:
            data["chatgpt"]["api_key"] = chatgpt_api_key.strip()
        if chatgpt_model is not None:
            data["chatgpt"]["model"] = chatgpt_model.strip()
        self._write(data)
        self._append_audit_entry(
            "update",
            {
                "whisper_api_key": bool(whisper_api_key),
                "whisper_model": bool(whisper_model),
                "chatgpt_api_key": bool(chatgpt_api_key),
                "chatgpt_model": bool(chatgpt_model),
            },
        )
        return data

    def _build_cipher(self, secret: Optional[str]) -> Optional[Fernet]:
        if not secret:
            return None
        normalized = secret.strip()
        try:
            if len(normalized) == 32:
                key = base64.urlsafe_b64encode(normalized.encode("utf-8"))
            else:
                # Assume caller already provided urlsafe base64 key
                key = normalized.encode("utf-8")
            return Fernet(key)
        except (ValueError, TypeError) as exc:
            raise RuntimeError("CREDENTIALS_SECRET_KEY invalida. Use chave urlsafe de 32 bytes.") from exc

    def _write(self, data: Dict[str, Dict[str, str]]) -> None:
        serialized = json.dumps(data, ensure_ascii=False).encode("utf-8")
        if not self._cipher:
            raise RuntimeError(
                "CREDENTIALS_SECRET_KEY precisa ser definido para escrever o cofre de credenciais."
            )
        payload: Any = {
            "version": 2,
            "encrypted": True,
            "payload": self._cipher.encrypt(serialized).decode("utf-8"),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        with self.lock:
            self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load_or_create_secret(self, force_new: bool = False) -> Tuple[str, bool]:
        if not force_new and self._secret_path.exists():
            try:
                cached = self._secret_path.read_text(encoding="utf-8").strip()
            except OSError:
                cached = ""
            if cached:
                return cached, True
        secret = self._generate_secret()
        try:
            self._secret_path.write_text(secret, encoding="utf-8")
        except OSError:
            pass
        return secret, False

    def _generate_secret(self) -> str:
        key = None
        try:
            key = Fernet.generate_key()
        except Exception:
            pass
        if key:
            return key.decode("utf-8")
        fallback = base64.urlsafe_b64encode(os.urandom(32))
        return fallback.decode("utf-8")

    def _reset_credentials(self) -> None:
        if self.path.exists():
            try:
                self.path.unlink()
            except OSError:
                pass
        if self._secret_path.exists():
            try:
                self._secret_path.unlink()
            except OSError:
                pass
        secret, _ = self._load_or_create_secret(force_new=True)
        self._cipher = self._build_cipher(secret)
        if not self._cipher:
            raise RuntimeError(
                "CREDENTIALS_SECRET_KEY precisa ser definido para usar o cofre de credenciais."
            )
        self._write(DEFAULT_CREDENTIALS)
        self._secret_loaded_from_cache = False

    def _append_audit_entry(self, action: str, metadata: Dict[str, Any]) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "metadata": metadata,
            "actor": os.getenv("USER") or os.getenv("USERNAME") or "system",
        }
        with self.audit_path.open("a", encoding="utf-8") as cursor:
            cursor.write(json.dumps(entry, ensure_ascii=False) + "\n")

    @staticmethod
    def _summarize_changes(data: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
        return {
            "whisper_api_key": bool(data.get("whisper", {}).get("api_key")),
            "whisper_model": data.get("whisper", {}).get("model"),
            "chatgpt_api_key": bool(data.get("chatgpt", {}).get("api_key")),
            "chatgpt_model": data.get("chatgpt", {}).get("model"),
        }


__all__ = ["RuntimeCredentialStore", "DEFAULT_CREDENTIALS"]
