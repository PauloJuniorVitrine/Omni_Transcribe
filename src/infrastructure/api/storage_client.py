from __future__ import annotations

import shutil
from pathlib import Path

from domain.ports.services import StorageClient


class LocalStorageClient(StorageClient):
    """Stores backups locally (e.g., backup/ folder)."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def upload(self, local_path: Path, remote_key: str) -> str:
        destination = self.base_dir / remote_key
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(local_path, destination)
        return str(destination)


class S3StorageClient(StorageClient):
    """Uploads files to an S3-compatible bucket (AWS, MinIO)."""

    def __init__(
        self,
        bucket: str,
        prefix: str = "",
        endpoint_url: str = "",
        access_key: str = "",
        secret_key: str = "",
        region: str = "",
        session_kwargs: dict | None = None,
    ) -> None:
        try:
            import boto3  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("boto3 precisa estar instalado para usar S3.") from exc

        self.bucket = bucket
        self.prefix = prefix.strip("/")
        client_kwargs = session_kwargs.copy() if session_kwargs else {}
        if endpoint_url:
            client_kwargs["endpoint_url"] = endpoint_url
        if region:
            client_kwargs["region_name"] = region
        if access_key and secret_key:
            client_kwargs["aws_access_key_id"] = access_key
            client_kwargs["aws_secret_access_key"] = secret_key
        self.client = boto3.client("s3", **client_kwargs)

    def upload(self, local_path: Path, remote_key: str) -> str:
        key = f"{self.prefix}/{remote_key}".strip("/") if self.prefix else remote_key
        self.client.upload_file(str(local_path), self.bucket, key)
        return f"s3://{self.bucket}/{key}"
