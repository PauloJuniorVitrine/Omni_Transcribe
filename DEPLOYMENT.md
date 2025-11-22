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
MAX_AUDIO_SIZE_MB=8192
MAX_REQUEST_BODY_MB=200
OPENAI_CHUNK_TRIGGER_MB=200
OPENAI_CHUNK_DURATION_SEC=900
ACCURACY_THRESHOLD=0.99
SESSION_TTL_MINUTES=720
ALLOWED_DOWNLOAD_EXTENSIONS=txt,srt,vtt,json,zip
OAUTH_CLIENT_ID=...
OAUTH_CLIENT_SECRET=...
OAUTH_AUTHORIZE_URL=...
OAUTH_TOKEN_URL=...
OAUTH_REDIRECT_URI=https://app.suaempresa.com/auth/callback
ALERT_WEBHOOK_URL=
METRICS_WEBHOOK_URL=
CORS_ALLOWED_ORIGINS=https://app.suaempresa.com,https://console.suaempresa.com
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOWED_METHODS=GET,POST,PUT,DELETE,OPTIONS
CORS_ALLOWED_HEADERS=content-type,authorization,x-csrf-token
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
- Downloads: quando a flag `downloads.signature_required` estiver ativa, os links usam token HMAC (`token` + `expires`); acione `/health` para checar status básico. Rate-limit aplicado em downloads e APIs de logs/resumo/incidentes (429), desativado em TEST_MODE. Limite de upload padrão via GUI: 2 GB (`MAX_REQUEST_BODY_MB`), suficiente para áudios longos (chunking automático acima de 200 MB).
- CORS: defina `CORS_ALLOWED_ORIGINS` com domínios reais; `CORS_ALLOW_CREDENTIALS=true` se usar cookies/sessão. Defaults são permissivos (`*`); restrinja em produção.
  - Guard: se `APP_ENV=production` e `CORS_ALLOWED_ORIGINS` contém `*`, o serviço não sobe (fail-fast).

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
- Workflow `.github/workflows/system-validation.yml` roda: validate_secrets → SAST/secret scan (Bandit, Trivy, ESLint) → unit/integration → e2e → load → build exe → installer → smoke → publish.
- Build: gera `TranscribeFlow.exe` e `TranscribeFlow-<versao>.exe` (tag ou `ci-<run>`). Installer é empacotado com ambos.
- Assinatura opcional: defina `SIGNING_CERT_BASE64` (PFX base64) e `SIGNING_CERT_PASSWORD`; passo de assinatura roda no Windows runner.
- Secrets requeridos: `CREDENTIALS_SECRET_KEY`, `OPENAI_API_KEY`; opcionais: `SIGNING_CERT_BASE64`, `SIGNING_CERT_PASSWORD`, `RUNTIME_CREDENTIALS_KEY`, `ALERT_WEBHOOK_URL`.

## 7. Checklist pre-deploy
- [ ] `npm run lint:js`, `npm run test:js`, `npm run test:e2e`
- [ ] `pytest -q`
- [ ] `scripts/report_accuracy_metrics.py`
- [ ] Secrets definidos no provedor
- [ ] `config/runtime_credentials.json` apenas payload criptografado (sem chaves reais)
- [ ] (Opcional) Assinatura aplicada ao EXE/installer se certificados configurados
