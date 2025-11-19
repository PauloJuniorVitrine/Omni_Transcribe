from pathlib import Path
path = Path('tests/integration/test_http_api.py')
text = path.read_text()
lines = text.splitlines()
start = end = None
for i,line in enumerate(lines):
    if line.startswith('def test_api_settings_page_allows_updates'):
        start = i
    if start is not None and line.strip() == '' and i > start:
        end = i
        break
if start is None:
    raise SystemExit('start not found')
if end is None:
    end = start + 12
new_block = [
    'def test_api_settings_page_allows_updates(tmp_path, monkeypatch):',
    '    global app',
    '    store = RuntimeCredentialStore(tmp_path / "runtime_credentials.json")',
    '    monkeypatch.setattr(http_app, "_runtime_store", store)',
    '    monkeypatch.setattr(config, "_runtime_store", store)',
    '',
]
lines = lines[:start] + new_block + lines[end:]
path.write_text('\n'.join(lines))
