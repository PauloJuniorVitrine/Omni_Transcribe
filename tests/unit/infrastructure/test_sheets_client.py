from __future__ import annotations

import types
from pathlib import Path
import sys
import json

from infrastructure.api.sheets_client import GoogleSheetsGateway


def _setup_stub_modules(monkeypatch, target_rows):
    gspread = types.ModuleType("gspread")

    class Worksheet:
        def append_row(self, row, value_input_option=None):
            target_rows.append((row, value_input_option))

    class Workbook:
        def __init__(self):
            self._worksheet = Worksheet()

        def worksheet(self, name):
            return self._worksheet

    class Client:
        def open_by_key(self, key):
            self.key = key
            return Workbook()

    def authorize(credentials):
        return Client()

    gspread.authorize = authorize
    monkeypatch.setitem(sys.modules, "gspread", gspread)

    google_oauth = types.ModuleType("google.oauth2.service_account")

    class Credentials:
        @staticmethod
        def from_service_account_file(path, scopes):
            return {"path": str(path), "scopes": tuple(scopes)}

    google_oauth.Credentials = Credentials
    monkeypatch.setitem(sys.modules, "google.oauth2.service_account", google_oauth)


def test_google_sheets_gateway_appends(monkeypatch, tmp_path):
    target_rows = []
    _setup_stub_modules(monkeypatch, target_rows)
    credentials = tmp_path / "credentials.json"
    credentials.write_text(json.dumps({"dummy": True}))

    gateway = GoogleSheetsGateway(
        credentials_path=credentials,
        spreadsheet_id="sheet-123",
        worksheet_name="Jobs",
    )
    row = {"job_id": "job1", "status": "approved"}
    gateway.append_row(row)

    assert target_rows
    assert target_rows[0][0] == list(row.values())
