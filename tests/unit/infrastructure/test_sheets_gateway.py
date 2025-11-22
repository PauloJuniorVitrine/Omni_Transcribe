from __future__ import annotations

import sys
import types

import pytest


def test_google_sheets_gateway_appends_row(monkeypatch):
    calls = []

    class _StubWorksheet:
        def append_row(self, values, value_input_option="USER_ENTERED"):
            calls.append((values, value_input_option))

    class _StubClient:
        def open_by_key(self, key):
            assert key == "sheet-id"
            return types.SimpleNamespace(worksheet=lambda name: _StubWorksheet())

    class _StubGSpread:
        def authorize(self, credentials):
            return _StubClient()

    class _StubCredentials:
        @classmethod
        def from_service_account_file(cls, path, scopes):
            return ("creds", path, scopes)

    # inject stubs before import
    monkeypatch.setitem(sys.modules, "gspread", _StubGSpread())
    google_auth_module = types.SimpleNamespace(service_account=types.SimpleNamespace(Credentials=_StubCredentials))
    monkeypatch.setitem(sys.modules, "google", types.SimpleNamespace(oauth2=google_auth_module))
    monkeypatch.setitem(sys.modules, "google.oauth2", google_auth_module)
    monkeypatch.setitem(sys.modules, "google.oauth2.service_account", types.SimpleNamespace(Credentials=_StubCredentials))

    from infrastructure.api.sheets_client import GoogleSheetsGateway

    gateway = GoogleSheetsGateway(credentials_path="creds.json", spreadsheet_id="sheet-id", worksheet_name="Jobs")
    gateway.append_row({"a": 1, "b": 2})

    assert calls == [([1, 2], "USER_ENTERED")]
