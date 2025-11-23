from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from application.services.ports import SheetGateway


class GoogleSheetsGateway(SheetGateway):
    """Google Sheets adapter using a service account."""

    def __init__(self, credentials_path: Path, spreadsheet_id: str, worksheet_name: str) -> None:
        try:
            import gspread  # type: ignore
            from google.oauth2.service_account import Credentials  # type: ignore
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("gspread e google-auth precisam estar instalados para usar Google Sheets.") from exc

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        credentials = Credentials.from_service_account_file(str(credentials_path), scopes=scopes)
        client = gspread.authorize(credentials)
        self.worksheet = client.open_by_key(spreadsheet_id).worksheet(worksheet_name)

    def append_row(self, row: Dict[str, Any]) -> None:
        values = list(row.values())
        self.worksheet.append_row(values, value_input_option="USER_ENTERED")
