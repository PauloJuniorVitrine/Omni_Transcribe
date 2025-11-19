# Deploy – TranscribeFlow

Este guia resume os passos necessários para subir o TranscribeFlow em staging ou produção.

## 1. Pré-requisitos

- **Python 3.11+** e **Node 20+**
- Dependências do sistema: `ffmpeg` (para Whisper local), `libasound2-dev`, `libpq` (se usar Postgres)
- Banco de dados e armazenamento configurados (por padrão CSV/JSON em disco)
- Credenciais das APIs (OpenAI Whisper, ChatGPT) e webhooks externos

## 2. Variáveis obrigatórias

Crie um `.env` (ou use secrets no provedor) com, no mínimo:

```ini
APP_ENV=production
CREDENTIALS_SECRET_KEY=<chave urlsafe 32 bytes>
OPENAI_API_KEY=<chave real>
OAUTH_CLIENT_ID=...
OAUTH_CLIENT_SECRET=...
OAUTH_AUTHORIZE_URL=...
OAUTH_TOKEN_URL=...
OAUTH_REDIRECT_URI=https://app.suaempresa.com/auth/callback
ALERT_WEBHOOK_URL=https://hooks.slack.com/services/xxx/yyy/zzz
METRICS_WEBHOOK_URL=
BASE_INPUT_DIR=/var/transcribeflow/inbox
BASE_OUTPUT_DIR=/var/transcribeflow/output
BASE_PROCESSING_DIR=/var/transcribeflow/processing
DATABASE_URL=postgresql+asyncpg://user:pass@host/db (se aplicável)
```

> **Importante:** `CREDENTIALS_SECRET_KEY` é obrigatório desde o bootstrap; sem ele o runtime store não levanta.

## 3. Instalando dependências

```bash
python -m venv .venv
source .venv/bin/activate  # (Linux/macOS)
pip install --upgrade pip
pip install -r requirements.txt

npm ci
npx playwright install --with-deps  # somente para rodar E2E
```

## 4. Executando a API/worker

### Servidor HTTP (FastAPI + Uvicorn)

```bash
uvicorn interfaces.http.app:app --host 0.0.0.0 --port 8000 --proxy-headers
```

Configure seu reverse proxy (Nginx/Traefik) para encaminhar `/` → Uvicorn e proteger via HTTPS.

### Watcher (ingestão de áudios)

```bash
python scripts/watch_inbox.py --config .env
```

O watcher monitora `BASE_INPUT_DIR` e dispara o pipeline para cada arquivo novo.

### Trabalhos manuais

Use `python scripts/run_job.py --job-id <ID>` para reprocessar manualmente via CLI.

## 5. Relatórios e telemetria

- `python scripts/report_accuracy_metrics.py` (gera `docs/accuracy_metrics_summary.md`)
- Logs em `logs/metrics.log` e `logs/alerts.log`, com envio paralelo para `ALERT_WEBHOOK_URL`/`METRICS_WEBHOOK_URL`

## 6. CI/CD

O workflow `.github/workflows/ci.yml` já executa lint/test JS, pytest, pip-audit e Playwright. Configure no GitHub:

- `CREDENTIALS_SECRET_KEY`
- `OPENAI_API_KEY`
- `ALERT_WEBHOOK_URL` (opcional)

## 7. Checklist pré-deploy

- [ ] `npm run lint:js`, `npm run test:js`, `npm run test:e2e`
- [ ] `pytest -q`
- [ ] `scripts/report_accuracy_metrics.py` (atualize o relatório anexado à release)
- [ ] Secrets definidos no provedor
- [ ] `config/runtime_credentials.json` contém apenas payload criptografado (sem chaves reais)

Com essas etapas, o sistema fica pronto para ser rodado em staging/produção de forma segura.
