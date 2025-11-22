from __future__ import annotations

import sys
from pathlib import Path

from infrastructure.api.storage_client import LocalStorageClient, S3StorageClient


def test_local_storage_upload_copies_file(tmp_path):
    base = tmp_path / "dest"
    client = LocalStorageClient(base)
    src = tmp_path / "sample.txt"
    src.write_text("hello", encoding="utf-8")

    dest = client.upload(src, "folder/file.txt")

    copied = base / "folder" / "file.txt"
    assert copied.exists()
    assert copied.read_text(encoding="utf-8") == "hello"
    assert Path(dest).name == "file.txt"


def test_s3_storage_client_uses_boto3_stub(monkeypatch, tmp_path):
    uploads: list[tuple[str, str, str]] = []

    class _StubBotoClient:
        def upload_file(self, local_path: str, bucket: str, key: str) -> None:
            uploads.append((local_path, bucket, key))

    class _StubBoto3:
        def client(self, *_args, **_kwargs):
            return _StubBotoClient()

    monkeypatch.setitem(sys.modules, "boto3", _StubBoto3())

    client = S3StorageClient(bucket="bkt", prefix="pre")
    src = tmp_path / "src.txt"
    src.write_text("x", encoding="utf-8")

    uri = client.upload(src, "folder/file.txt")

    assert uri == "s3://bkt/pre/folder/file.txt"
    assert uploads == [(str(src), "bkt", "pre/folder/file.txt")]
