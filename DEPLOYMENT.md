# Deploy - TranscribeFlow

Guia resumido para subir o TranscribeFlow em staging ou producao.

## 1. Pre-requisitos
- Python 3.11+ e Node 20+
- Dependencias de sistema: `ffmpeg` (para Whisper local); `libasound2-dev`; `libpq` se usar Postgres
- Armazenamento: por padrao CSV/JSON em disco (sem banco SQL)
- Credenciais das APIs (OpenAI Whisper/ChatGPT) e webhooks externos

## 2. Variaveis obrigatorias (.env ou secrets)
```
APP_ENV=production
CREDENTIALS_SECRET_KEY=<chave urlsafe 32 bytes>
OPENAI_API_KEY=<chave real>
OAUTH_CLIENT_ID=...
OAUTH_CLIENT_SECRET=...
OAUTH_AUTHORIZE_URL=...
OAUTH_TOKEN_URL=...
OAUTH_REDIRECT_URI=https://app.suaempresa.com/auth/callback
ALERT_WEBHOOK_URL=
METRICS_WEBHOOK_URL=
BASE_INPUT_DIR=/var/transcribeflow/inbox
BASE_OUTPUT_DIR=/var/transcribeflow/output
BASE_PROCESSING_DIR=/var/transcribeflow/processing
```
> CREDENTIALS_SECRET_KEY e obrigatoria para o cofre em `config/runtime_credentials.json`.

## 3. Instalacao
```
python -m venv .venv
.\.venv\Scripts\activate   # Windows
source .venv/bin/activate  # Linux/macOS
pip install --upgrade pip
pip install -r requirements.txt

npm ci
npx playwright install --with-deps   # se for rodar E2E
```

## 4. Execucao
### GUI / HTTP (FastAPI + Uvicorn)
```
python launcher_gui.py --host 0.0.0.0 --port 8000
```
- Scripts de atalho para Windows: `scripts/run_with_gui.ps1`, `scripts/run_transcribeflow.ps1`, `scripts/run_transcribeflow.bat` (todos chamam `launcher_gui.py`, sem TranscribeFlow.exe).
- Configure reverse proxy (Nginx/Traefik) apontando `/` para Uvicorn e proteja com HTTPS.
- GUI cobre: dashboard, incidentes, logs, revisao, downloads com token, upload de audio (criando job), flags e templates, credenciais runtime.

### Watcher (ingestao de audios)
```
python scripts/watch_inbox.py
```

### CLI manual
```
python -m interfaces.cli.run_job --file inbox/exemplo.wav --profile geral
python -m interfaces.cli.run_job --job-id <ID>
```

## 5. Relatorios e telemetria
- `python scripts/report_accuracy_metrics.py` gera `docs/accuracy_metrics_summary.md`
- Logs: `logs/metrics.log` e `logs/alerts.log` (webhooks via ALERT_WEBHOOK_URL/METRICS_WEBHOOK_URL)

## 6. CI/CD
- Workflow `.github/workflows/ci.yml` roda lint/test JS, pytest, pip-audit, Playwright
- Secrets requeridos: `CREDENTIALS_SECRET_KEY`, `OPENAI_API_KEY`, opcional `ALERT_WEBHOOK_URL`

## 7. Checklist pre-deploy
- [ ] `npm run lint:js`, `npm run test:js`, `npm run test:e2e`
- [ ] `pytest -q`
- [ ] `scripts/report_accuracy_metrics.py`
- [ ] Secrets definidos no provedor
- [ ] `config/runtime_credentials.json` apenas payload criptografado (sem chaves reais)
