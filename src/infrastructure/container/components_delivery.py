from __future__ import annotations

from pathlib import Path

from application.services.package_service import ZipPackageService
from application.services.rejected_logger import FilesystemRejectedLogger
from application.services.sheet_service import CsvSheetService
from application.services.status_publisher import SheetStatusPublisher
from config import Settings
from domain.usecases.register_delivery import RegisterDelivery
from infrastructure.api.gotranscript_client import GoTranscriptClient
from infrastructure.api.sheets_client import GoogleSheetsGateway
from infrastructure.api.storage_client import S3StorageClient


def build_logging_and_sheet(settings: Settings):
    sheet_gateway = _build_sheet_gateway(settings)
    sheet_service = CsvSheetService(Path(settings.csv_log_path), sheet_gateway=sheet_gateway)
    status_publisher = SheetStatusPublisher(sheet_service)
    rejected_logger = FilesystemRejectedLogger(Path(settings.base_rejected_dir))
    return sheet_service, status_publisher, rejected_logger


def build_delivery_services(settings: Settings, job_repository, artifact_repository, sheet_service, log_repository):
    storage_client = _build_storage_client(settings)
    delivery_client = _build_delivery_client(settings)
    package_service = ZipPackageService(Path(settings.base_backup_dir), storage_client=storage_client)
    register_delivery = RegisterDelivery(
        job_repository=job_repository,
        artifact_repository=artifact_repository,
        package_service=package_service,
        delivery_logger=sheet_service,
        log_repository=log_repository,
        delivery_client=delivery_client,
    )
    return package_service, register_delivery


def _build_sheet_gateway(settings: Settings):
    if not settings.google_sheets_enabled:
        return None
    if not settings.google_sheets_spreadsheet_id:
        raise RuntimeError("GOOGLE_SHEETS_SPREADSHEET_ID precisa ser definido.")
    return GoogleSheetsGateway(
        credentials_path=settings.google_sheets_credentials_path,
        spreadsheet_id=settings.google_sheets_spreadsheet_id,
        worksheet_name=settings.google_sheets_worksheet,
    )


def _build_storage_client(settings: Settings):
    if not settings.s3_enabled:
        return None
    return S3StorageClient(
        bucket=settings.s3_bucket,
        prefix=settings.s3_prefix,
        endpoint_url=settings.s3_endpoint_url,
        access_key=settings.s3_access_key,
        secret_key=settings.s3_secret_key,
        region=settings.s3_region,
    )


def _build_delivery_client(settings: Settings):
    if not settings.gotranscript_enabled:
        return None
    return GoTranscriptClient(
        base_url=settings.gotranscript_base_url,
        api_key=settings.gotranscript_api_key,
        timeout=settings.gotranscript_timeout_sec,
    )
